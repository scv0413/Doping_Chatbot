# Request ID and JSON Structured Logging

## 목적

Docker/FastAPI API를 운영 가능한 형태로 만들기 위해 request 단위 추적성을 추가했다. 이제 클라이언트 응답, 에러 응답, 서버 로그를 같은 `request_id`로 연결할 수 있다.

## 구현

```text
app/chat/interfaces/api/logging.py
app/chat/interfaces/api/errors.py
tests/chat/api/test_api.py
```

## Request ID 정책

- 클라이언트가 `X-Request-ID`를 보내면 그대로 사용한다.
- 없으면 서버가 UUID를 생성한다.
- 모든 응답 header에 `X-Request-ID`를 넣는다.
- API error body에도 `request_id`를 넣는다.
- JSON request log에도 같은 `request_id`를 넣는다.

## JSON Log 예시

```json
{
  "timestamp": "2026-07-22 08:01:55,283",
  "level": "INFO",
  "logger": "app.chat.interfaces.api",
  "message": "request_completed",
  "request_id": "docker-json-validation-1",
  "method": "POST",
  "path": "/api/v1/chat-responses",
  "status_code": 422,
  "duration_ms": 6.51
}
```

## 오류와 해결

### 500 응답에서 request_id header 누락

처음에는 `ContextVar`만 사용했다. 하지만 unhandled exception 흐름에서는 exception handler가 middleware context 밖에서 응답을 만들 수 있어 500 응답에 `X-Request-ID` header가 누락되었다.

해결:

- middleware에서 `request.state.request_id`에도 저장
- error handler는 `request.state.request_id`를 우선 읽고, 없으면 ContextVar fallback 사용

### root logger 오염 문제

초기 JSON logging 설정은 root logger handler를 교체했다. 이 때문에 Gradio analytics background thread가 테스트 종료 후 closed stdout에 로그를 쓰며 logging error를 냈다.

해결:

- root logger가 아니라 `app.chat` logger에만 JSON handler 적용
- `app.chat` logger propagation 비활성화
- Uvicorn access log는 Docker CMD에서 `--no-access-log`로 비활성화

## Docker 검증

성공 응답:

```text
GET /health with X-Request-ID: docker-json-log-request-1
-> response header x-request-id: docker-json-log-request-1
```

Validation error:

```text
POST /api/v1/chat-responses with X-Request-ID: docker-json-validation-1
-> response header x-request-id: docker-json-validation-1
-> error.request_id: docker-json-validation-1
-> JSON log request_id: docker-json-validation-1
```

## 검증 결과

- `uv run pytest tests/chat/api`: 11 passed
- `uv run pytest`: 98 passed, 1 LangSmith dependency warning
- `uv run ruff check app tests`: pass
- `uv run python -m compileall app tests`: pass
- `docker compose build api`: pass
- `docker compose up -d api`: pass
- Docker request_id header/body/log 검증: pass
