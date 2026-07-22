# API Error Response Standard

## 목적

FastAPI 기본 에러 응답, validation error, 예상치 못한 서버 오류를 하나의 응답 형태로 표준화했다. 외부 클라이언트와 Docker 배포 환경에서 실패 응답을 예측 가능하게 만들기 위한 작업이다.

## 표준 에러 응답

모든 API error는 다음 envelope를 사용한다.

```json
{
  "error": {
    "code": "validation_error",
    "message": "요청 형식이 올바르지 않습니다.",
    "details": []
  }
}
```

## Error Codes

### `validation_error`

요청 body, query parameter, path parameter 검증 실패다. HTTP status는 `422`다.

예시:

```json
{
  "error": {
    "code": "validation_error",
    "message": "요청 형식이 올바르지 않습니다.",
    "details": [
      {
        "loc": ["body", "query"],
        "message": "String should have at least 1 character",
        "type": "string_too_short"
      }
    ]
  }
}
```

### `http_error`

FastAPI/Starlette HTTPException 계열이다. 예를 들어 존재하지 않는 endpoint는 `404`와 함께 이 code를 반환한다.

### `internal_server_error`

예상하지 못한 서버 예외다. HTTP status는 `500`이며 내부 exception message는 클라이언트에 직접 노출하지 않는다. 상세 내용은 server log에 남긴다.

## Runtime Errors와의 관계

`ChatResponse.errors`는 pipeline 내부 tool 오류를 사용자에게 전달하기 위한 성공 응답의 일부다. 예를 들어 retrieval 실패 후 fallback 답변을 생성할 수 있다면 HTTP 200과 함께 `errors`에 stage 정보를 담는다.

반면 API exception handler는 request validation 실패, 존재하지 않는 endpoint, route 함수에서 처리되지 않은 예외처럼 HTTP 실패로 보아야 하는 경우에만 사용한다.

## 구현 파일

```text
app/chat/api/errors.py
app/chat/api/main.py
tests/chat/api/test_api.py
```

## 검증

로컬 테스트:

```bash
uv run pytest tests/chat/api
# 7 passed

uv run pytest
# 94 passed, 1 LangSmith dependency warning
```

Docker HTTP 검증:

```bash
POST /api/v1/chat-responses with invalid body -> 422
GET /missing -> 404
GET /ready -> 200
```

Docker validation error 응답:

```json
{
  "error": {
    "code": "validation_error",
    "message": "요청 형식이 올바르지 않습니다.",
    "details": [
      {"loc": ["body", "query"], "message": "String should have at least 1 character", "type": "string_too_short"},
      {"loc": ["body", "top_k"], "message": "Input should be greater than or equal to 1", "type": "greater_than_equal"}
    ]
  }
}
```

## 발견한 오류와 수정

처음에는 `status.HTTP_422_UNPROCESSABLE_ENTITY`를 사용했는데, 현재 Starlette/FastAPI 조합에서 deprecation warning이 발생했다. `status.HTTP_422_UNPROCESSABLE_CONTENT`로 교체해 warning을 제거했다.

## 다음 개선

- error `request_id` 추가
- JSON structured logging
- domain-specific error code 추가
- API response examples를 OpenAPI schema에 추가
