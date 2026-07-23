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

`app/chat/interfaces/api/logging.py`를 추가했다. FastAPI middleware에서 요청마다 다음 정보를 남긴다.

- HTTP method
- path
- status_code
- duration_ms

로그 예시:

```json
{"timestamp":"2026-07-22 09:18:10,517","level":"INFO","logger":"app.chat.interfaces.api","message":"request_completed","request_id":"smoke-public-env","method":"POST","path":"/api/v1/chat-responses","status_code":200,"duration_ms":4739.24}
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
- `uv run pytest`: 121 passed, 1 LangSmith dependency warning
- `uv run python -m compileall app tests`: pass
- Docker build: pass
- Docker run: pass
- Docker health/readiness: pass

## 다음 개선 후보

- `/ready`에서 Chroma collection count까지 확인하는 deeper readiness
- Docker image size 최적화
- container resource limits 설정
- vector index volume 백업 전략
- CI에서 docker compose 기반 smoke test로 확장
- staging 환경에서 secret을 주입한 실제 chat smoke 자동화


## 2026-07-22 API/UI Final Docker Smoke

API/UI 최종 정리 후 Docker image를 실제로 build/run smoke test 했다.

Build:

```bash
docker build -t doping-chatbot-api:local-smoke .
# success
```

Run:

```bash
docker run -d \
  --name doping-chatbot-api-smoke \
  -p 8011:8000 \
  --env-file .env \
  -e APP_ENV=smoke \
  -v "$PWD/data:/app/data" \
  doping-chatbot-api:local-smoke
```

Non-root 검증:

```bash
docker exec doping-chatbot-api-smoke id
# uid=999(appuser) gid=999(appuser) groups=999(appuser)
```

Endpoint smoke:

- `GET /health`: 200, `X-Request-ID` echo 확인
- `GET /ready`: 200, `status=ready`
- `POST /api/v1/chat-responses`: 200, public request는 `query`만 사용
- `POST /api/v1/chat-responses` with `top_k`: 422, extra field 거부 확인
- `POST /api/v1/debug/chat-responses`: 200, internal options 허용
- public/debug chat 모두 retrieval citation 반환, errors 없음

발견한 점:

- `.env` 없이 직접 `docker run`하면 OpenAI credential이 없어 retrieval 단계가 실패한다.
- `docker-compose.yml`은 `env_file: .env`를 사용하므로 운영 실행에서는 secret/env 주입이 필요하다.
- CI는 secret 없는 환경을 고려해 `/health`, `/ready`까지만 smoke test한다. chat endpoint까지 CI에서 테스트하려면 mock provider 또는 secret 주입 전략이 필요하다.

정리:

- Docker build: pass
- Docker run: pass
- non-root: pass
- readiness: pass
- JSON request logging: pass
- public/debug API split: pass


## CI Readiness 기준 정리

CI에서 Docker image를 build한 뒤 실행하는 컨테이너에는 `.env`, `data/processed`, `data/indexes`가 주입되지 않는다. 따라서 CI 컨테이너의 `/ready`는 `ready`가 아니라 `not_ready`일 수 있다.

이 상태는 실패가 아니다. CI의 목적은 다음을 확인하는 것이다.

- image build 성공
- FastAPI process start 성공
- container가 non-root user로 실행됨
- `/health`가 200과 `status=ok`를 반환
- `/ready`가 200과 readiness JSON shape를 반환

반대로 실제 staging/운영 smoke에서는 data volume, Chroma index, API key가 주입되어야 하므로 `scripts/staging_smoke.py`가 `/ready`의 `status=ready`를 요구한다.

정리하면 다음과 같다.

| 환경 | `/ready` 기대값 | 이유 |
|---|---|---|
| CI Docker build verification | `ready` 또는 `not_ready` JSON | secret/data 없이 image 구조만 검증 |
| Local/Staging smoke with data/env | `ready` | 실제 serving 준비 상태 검증 |

## Local Docker Verification 결과

실제 Docker Desktop 환경에서 다음을 확인했다.

```bash
docker build -t doping-chatbot-api:local-verify .
docker run -d --name doping-chatbot-api-local-verify -p 8011:8000 -e APP_ENV=local-verify doping-chatbot-api:local-verify
docker exec doping-chatbot-api-local-verify id -u
```

결과:

- Docker build: pass
- container user id: `999`, non-root pass
- `GET /health`: `status=ok` pass
- `GET /ready`: `status=not_ready`, readiness JSON shape pass

`not_ready`의 원인은 검증 컨테이너에 chunk/index/API key를 주입하지 않았기 때문이다. 실제 staging은 `docker-compose.yml`의 volume/env 또는 배포 환경 secret으로 이를 주입한 뒤 `scripts/staging_smoke.py`로 확인한다.
