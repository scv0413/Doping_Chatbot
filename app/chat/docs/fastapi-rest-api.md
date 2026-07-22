# FastAPI REST API Wrapper

## 목적

Gradio와 FastAPI가 내부 graph, pipeline, retrieval, drug search 구조를 직접 알지 않도록 `app.chat.runtime.run_chat`을 REST API로 감싸는 얇은 wrapper를 만들었다.

## 현재 REST 구조

```text
app/chat/api/
  __init__.py
  dependencies.py
  main.py
  routes.py
```

## Endpoint

### `GET /health`

서버 상태 확인용 endpoint다. Docker, 배포 플랫폼, 로드밸런서 health check에서 사용할 수 있다.

Response 예시:

```json
{
  "status": "ok",
  "app": "doping-chatbot",
  "env": "local"
}
```

### `GET /`

간단한 root endpoint다. API 문서 위치를 안내한다.

### `POST /api/v1/chat-responses`

사용자 질문을 받아 챗봇 답변 리소스를 생성한다. REST 관점에서 질문 처리 결과를 만드는 command 성격이므로 `POST`를 사용했다.

Public request body는 `query`만 받는다. `top_k`, `use_llm`, `engine`, `recursion_limit` 같은 내부 실행 옵션은 public API에서 받지 않는다. 이 값들은 Runtime Policy가 자동으로 결정한다.

```json
{
  "query": "새벽에 혈액 시료 채취를 요청받으면 어떻게 대응해야 해?"
}
```

### `POST /api/v1/debug/chat-responses`

내부 실험과 디버깅용 endpoint다. `app.chat.runtime.ChatRequest`를 그대로 받아 `top_k`, `use_llm`, `engine`, `recursion_limit`을 명시적으로 override할 수 있다.

이 endpoint는 운영 public UI가 아니라 개발자/평가/디버그 용도다.

## RESTful 판단

현재 API는 완전한 CRUD 리소스 API라기보다 inference API다. 따라서 `POST /api/v1/chat-responses`처럼 “답변 리소스를 생성한다”는 이름을 사용했다.

좋은 점:

- endpoint가 동사가 아니라 리소스명이다.
- version prefix `/api/v1`을 사용한다.
- public request schema가 `query` 중심으로 단순하다.
- 내부 실험 옵션은 debug endpoint로 분리했다.
- request/response schema가 Pydantic으로 고정되어 있다.
- API layer는 내부 graph/pipeline을 모르고 `run_chat`만 호출한다.

아직 보류한 endpoint:

- `POST /api/v1/drug-searches`
- `POST /api/v1/pharmacology-lookups`
- `POST /api/v1/retrieval-searches`

이 세 endpoint는 디버깅/관리자/개발자용으로 유용하지만, 사용자 MVP에서는 `chat-responses` 하나가 우선이다.

## Docker 고려

Docker 실행 command는 다음 형태가 된다.

```bash
uvicorn app.chat.api.main:app --host 0.0.0.0 --port 8000
```

Docker로 감쌀 때 확인할 것:

- `.env`는 image에 넣지 않고 runtime env로 주입한다.
- `data/indexes` 또는 Chroma 저장소는 volume으로 분리한다.
- `OPENAI_API_KEY`, `LANGSMITH_API_KEY`는 secret/env로 관리한다.
- `/health`를 container healthcheck로 사용한다.

## 검증

- `uv run ruff check app tests`: pass
- `uv run pytest`: 121 passed, 1 LangSmith dependency warning
- `uv run python -m compileall app tests`: pass
- `uv run uvicorn app.chat.api.main:app --host 127.0.0.1 --port 8010`: server start pass
- `GET /health`: 200 OK
- `GET /`: 200 OK
- `GET /docs`: 200 OK

## 발견한 오류와 수정

처음에는 root endpoint가 module-level `app`에는 붙지만 `create_app()`으로 만든 테스트 앱에는 붙지 않는 문제가 있었다. Docker와 테스트가 같은 app factory를 사용해야 하므로 root endpoint를 `create_app()` 내부에서 등록하도록 수정했다.

또한 app route inspection에서 FastAPI 내부 included router object를 단순 `app.routes`로만 판단하면 누락처럼 보일 수 있었다. 실제 HTTP 요청과 TestClient를 기준으로 검증했다.


## API/UI Final Cleanup

최종 사용자용 API는 `query`만 받도록 정리했다. 내부 실행 옵션은 Runtime Policy가 결정한다.

OpenAPI 확인 결과:

- `/api/v1/chat-responses`: `PublicChatRequest`, fields=`query` only, `additionalProperties=false`
- `/api/v1/debug/chat-responses`: `ChatRequest`, fields=`query`, `top_k`, `use_llm`, `engine`, `recursion_limit`

검증:

- public endpoint에 내부 옵션을 보내면 `422 validation_error`
- debug endpoint는 내부 옵션 허용
- 전체 테스트 `121 passed, 1 warning`
- 전체 lint `All checks passed`
