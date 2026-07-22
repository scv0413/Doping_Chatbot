# Docker Production Hardening

## 목적

FastAPI API wrapper를 실제 Docker container로 실행하고, 운영 배포 전 기본 방어선을 추가했다.

## 적용 내용

### 1. Non-root container user

Dockerfile에서 `appuser` system user/group을 만들고 `/app` 소유권을 넘긴 뒤 `USER appuser`로 실행한다.

검증:

```bash
docker exec doping-chatbot-api id
# uid=999(appuser) gid=999(appuser) groups=999(appuser)
```

### 2. Readiness endpoint

`GET /ready`를 추가했다.

`/health`는 프로세스 생존 확인에 가깝고, `/ready`는 serving에 필요한 runtime directory가 준비되었는지 확인한다. 현재 readiness check는 다음을 본다.

- `processed_data_dir`
- `index_dir`

응답 예시:

```json
{
  "status": "ready",
  "checks": [
    {"name": "processed_data_dir", "ready": true, "detail": "/app/data/processed"},
    {"name": "index_dir", "ready": true, "detail": "/app/data/indexes"}
  ]
}
```

Docker `HEALTHCHECK`와 compose healthcheck는 `/ready`를 기준으로 바꿨다.

### 3. Request logging

`app/chat/api/logging.py`를 추가했다. FastAPI middleware에서 요청마다 다음 정보를 남긴다.

- HTTP method
- path
- status_code
- duration_ms

로그 예시:

```text
INFO app.chat.api request_completed method=POST path=/api/v1/chat-responses status_code=200 duration_ms=6535.74
```

### 4. CI Docker build verification

`.github/workflows/docker-build.yml`을 추가했다. CI에서는 다음 순서로 검증한다.

1. checkout
2. Python 3.12 setup
3. uv setup
4. `uv sync --frozen --extra dev`
5. `uv run ruff check app tests`
6. `uv run pytest`
7. `docker build -t doping-chatbot-api:ci .`
8. container run
9. `/health`, `/ready` smoke test
10. failure 시 container logs 출력

## 실제 Docker 검증 결과

Docker Desktop 설치 후 실제 build/run을 수행했다.

```bash
docker compose build api
# Image doping-chatbot-api:local Built

docker compose up -d api
# Container doping-chatbot-api Started
```

HTTP 검증:

```bash
GET /health -> 200 OK
GET /ready  -> 200 OK, status=ready
GET /docs   -> 200 OK
POST /api/v1/chat-responses -> 200 OK
```

Container 상태:

```bash
docker compose ps
# Up ... (healthy)

docker inspect --format='{{.State.Health.Status}}' doping-chatbot-api
# healthy
```

Non-root 검증:

```bash
docker exec doping-chatbot-api id
# uid=999(appuser) gid=999(appuser) groups=999(appuser)
```

## 로컬 검증 결과

- `uv run ruff check app tests`: pass
- `uv run pytest`: 92 passed, 1 LangSmith dependency warning
- `uv run python -m compileall app tests`: pass
- Docker build: pass
- Docker run: pass
- Docker health/readiness: pass

## 다음 개선 후보

- `/ready`에서 Chroma collection count까지 확인하는 deeper readiness
- production logging을 JSON format으로 전환
- API error response 표준화
- Docker image size 최적화
- CI에서 docker compose 기반 smoke test로 확장
