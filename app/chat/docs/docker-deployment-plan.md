# Docker Deployment Plan

## 목적

FastAPI로 구성한 `app.chat.api.main:app`을 Docker container로 실행할 수 있도록 packaging 구조를 만들었다.

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
  -> uvicorn app.chat.api.main:app
  -> /health
  -> /api/v1/chat-responses
  -> runtime.run_chat
  -> graph/pipeline
```

## Dockerfile 설계

base image는 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`을 사용한다. 이유는 현재 프로젝트가 `uv` 기반이고, Docker build에서도 lockfile 기반 설치를 유지하기 위해서다.

핵심 명령:

```dockerfile
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-sync", "uvicorn", "app.chat.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
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

container 내부에서 `/health`를 호출한다. slim image에 curl을 추가하지 않기 위해 Python 표준 라이브러리 `urllib.request`를 사용한다.

```bash
uv run --no-sync python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"
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
  -d '{"query":"슈도에페드린 반감기가 얼마나 돼?","top_k":3,"use_llm":false,"engine":"graph"}'
```

## 현재 검증 결과

이 로컬 환경에는 Docker CLI가 설치되어 있지 않아 실제 `docker build`와 `docker run`은 수행하지 못했다. 대신 다음 검증을 완료했다.

- docker-compose YAML parse: pass
- Docker artifact tests: pass
- API tests: pass
- Ruff: pass
- Full pytest: 89 passed, 1 LangSmith dependency warning
- compileall: pass

## 다음 단계

Docker가 설치된 환경에서 실제 build/run을 수행한다. 이후 운영 배포를 고려하면 다음을 추가한다.

- non-root user 실행
- container resource limits
- production logging format
- `/ready` readiness endpoint
- vector index volume 백업 전략
- CI에서 docker build 검증
