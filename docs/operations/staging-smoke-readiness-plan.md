# Staging Smoke and Deeper Readiness Plan

## 목적

이 문서는 Docker 이후 실제 운영 또는 staging 환경으로 넘어가기 전에 필요한 검증 기준을 정리한다.
현재 프로젝트는 FastAPI, Gradio, Chroma index, OpenAI API, local data volume에 의존한다.
따라서 단순히 container가 켜졌는지만 보는 `/health`로는 충분하지 않다.

운영 검증은 세 단계로 나눈다.

1. process health
2. readiness
3. staging smoke

## 1. Process Health

### 목적

애플리케이션 프로세스가 살아 있는지 확인한다.

### Endpoint

```text
GET /health
```

### 기대 결과

```json
{
  "status": "ok"
}
```

### 검증 의미

- FastAPI process가 떠 있다.
- routing table이 로드되었다.
- 하지만 vector DB, index, OpenAI key, data volume까지 검증하지는 않는다.

## 2. Readiness

### 목적

서비스가 실제 요청을 받을 준비가 되었는지 확인한다.

### Endpoint

```text
GET /ready
```

### 현재 검증 기준

- app settings load 가능
- processed data path 확인
- Chroma index path 확인
- runtime entrypoint import 가능
- 필수 환경변수 존재 여부 확인

### deeper readiness에서 추가할 기준

현재 `/ready`는 기본 readiness다.
다음 단계에서는 더 깊은 readiness를 추가한다.

- Chroma collection count가 0보다 큰지
- sample retrieval query가 error 없이 수행되는지
- OpenAI API key가 runtime에서 접근 가능한지
- public API schema가 query-only인지
- debug API가 internal option을 받는지
- JSON logging에 request_id가 포함되는지

## 3. Staging Smoke

### 목적

배포된 staging 서버에서 실제 사용자 흐름이 깨지지 않는지 확인한다.

### Smoke 시나리오

| 번호 | 요청 | 기대 결과 |
|---|---|---|
| 1 | `GET /health` | 200, status ok |
| 2 | `GET /ready` | 200, status ready |
| 3 | public chat: `타이레놀 먹어도 돼?` | 200, answer 존재, errors 비어 있음 |
| 4 | public chat에 `top_k` 전달 | 422 validation_error |
| 5 | debug chat에 `top_k`, `use_llm`, `engine` 전달 | 200 |
| 6 | `X-Request-ID` header 전달 | response header와 structured log에 같은 id 포함 |

## 4. CI에서 Docker Build 검증

### 최소 기준

```text
uv run ruff check app tests
uv run pytest
uv run pytest tests/test_docker_artifacts.py
docker build -t doping-chatbot-api:ci .
```

### staging smoke는 왜 CI와 분리하나

CI는 build와 단위 테스트를 빠르게 검증한다.
staging smoke는 실제 환경변수, volume, network, API key, vector DB까지 포함하므로 CI보다 느리고 외부 의존성이 있다.
따라서 PR 단계에서는 build/test를 보고, 배포 직후 staging smoke를 별도 job으로 돌리는 것이 좋다.

## 5. 포트폴리오에서 설명할 포인트

이 프로젝트는 모델 호출 코드만 작성한 것이 아니라 실제 운영 표면을 고려했다.

- public API와 debug API를 분리했다.
- request_id로 장애 추적 가능성을 확보했다.
- JSON structured logging으로 로그 수집 시스템과 연결 가능하게 했다.
- Docker container를 non-root user로 실행했다.
- `/ready`를 통해 단순 process health와 실제 준비 상태를 분리했다.
- staging smoke 기준을 만들어 배포 후 기능이 살아 있는지 검증할 수 있게 했다.

## 6. 구현 반영 상태

현재 다음 항목은 구현되었다.

- `scripts/staging_smoke.py` 생성
- `/ready` deeper readiness 강화
- processed chunk file 존재 및 line count 확인
- Chroma persistent collection count 확인
- OpenAI API key 존재 확인
- `run_chat` runtime import 확인
- public/debug API smoke 기준 반영

## 7. 다음 구현 후보

1. GitHub Actions 또는 CI 문서에 Docker build step 추가
2. staging 배포 후 smoke 실행 자동화
3. smoke script 결과를 JSON artifact로 저장
4. `/ready`에 optional sample retrieval check 추가
