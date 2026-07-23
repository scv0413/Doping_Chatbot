# Docker Deployment Plan

## 목적

FastAPI로 구성한 `app.chat.interfaces.api.main:app`을 Docker container로 실행할 수 있도록 packaging 구조를 만들었다.

## 추가 파일

```text
Dockerfile
.dockerignore
docker-compose.yml
tests/test_docker_artifacts.py
```

## 실행 구조

```text
Docker container
  -> uvicorn app.chat.interfaces.api.main:app
  -> /health / /ready
  -> /api/v1/chat-responses or /api/v1/debug/chat-responses
  -> runtime.run_chat
  -> graph/pipeline
```

## Dockerfile 설계

base image는 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`을 사용한다. 이유는 현재 프로젝트가 `uv` 기반이고, Docker build에서도 lockfile 기반 설치를 유지하기 위해서다.

핵심 명령:

```dockerfile
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-sync", "uvicorn", "app.chat.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
```

## Runtime Data Strategy

image에는 코드와 dependency만 포함한다. 다음 데이터는 image에 넣지 않는다.

- `.env`
- `data/raw`
- `data/processed`
- `data/indexes`
- `logs`

이유는 다음과 같다.

- API key와 secret이 image에 들어가면 안 된다.
- Chroma index와 processed data는 교체/재생성 가능해야 한다.
- Docker image는 가능한 작고 재현 가능해야 한다.

`docker-compose.yml`에서는 다음 volume을 사용한다.

```yaml
volumes:
  - ./data:/app/data
```

## Healthcheck

container 내부에서 `/ready`를 호출한다. slim image에 curl을 추가하지 않기 위해 Python 표준 라이브러리 `urllib.request`를 사용한다.

```bash
uv run --no-sync python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()"
```

## Local Docker Commands

Docker가 설치된 환경에서는 다음 순서로 실행한다.

```bash
docker compose build
docker compose up api
```

검증:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs
```

chat API 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat-responses \
  -H "Content-Type: application/json" \
  -d '{"query":"슈도에페드린 반감기가 얼마나 돼?"}'

# 내부 실험용 옵션은 debug endpoint에서만 사용
curl -X POST http://127.0.0.1:8000/api/v1/debug/chat-responses \
  -H "Content-Type: application/json" \
  -d '{"query":"슈도에페드린 반감기가 얼마나 돼?","top_k":3,"use_llm":false,"engine":"graph"}'
```

## 현재 검증 결과

Docker Desktop 설치 후 실제 `docker build`와 `docker run` smoke test를 완료했다.

- Docker artifact tests: pass
- Docker version: 29.6.2
- Docker Compose version: v5.3.1
- `docker build -t doping-chatbot-api:local-smoke .`: pass
- `docker run ... --env-file .env ...`: pass
- non-root user: `uid=999(appuser)`
- `GET /health`: 200
- `GET /ready`: 200, `status=ready`
- public chat endpoint: 200, retrieval citations returned
- public endpoint rejects internal options: 422
- debug chat endpoint: 200, internal options accepted
- JSON request logging with request_id: pass
- `uv run pytest`: 121 passed, 1 LangSmith dependency warning
- `uv run ruff check app tests`: pass

## 다음 단계

Docker build/run smoke까지 완료했으므로 다음 개선 후보는 운영 안정성 확장이다.

- `/ready`에서 Chroma collection count까지 확인하는 deeper readiness
- container resource limits 설정
- vector index volume 백업 전략
- staging 환경에서 실제 chat smoke 자동화
- secret 없는 CI에서는 mock provider 기반 chat smoke 검토
