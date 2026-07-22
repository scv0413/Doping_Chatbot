# Staging Smoke and Readiness

## 목적

운영 또는 Docker 배포 직전에 API 서버가 최소 기능을 수행할 준비가 되었는지 확인한다.

Readiness는 서버 내부 의존성을 확인하고, staging smoke는 외부 HTTP 관점에서 주요 endpoint가 기대대로 동작하는지 확인한다.

## `/ready` Readiness Checks

`GET /ready`는 다음 항목을 확인한다.

| Check | 의미 |
|---|---|
| `processed_data_dir` | 전처리 데이터 디렉토리 존재 여부 |
| `processed_chunks` | chunk jsonl 파일 존재 및 non-empty 여부 |
| `index_dir` | vector index 루트 디렉토리 존재 여부 |
| `chroma_directory` | Chroma persist directory 존재 여부 |
| `chroma_collection` | Chroma collection 접근 및 count > 0 여부 |
| `openai_api_key` | OpenAI API key 설정 여부 |
| `runtime_import` | `run_chat` import 가능 여부 |
| `runtime_policy_import` | `decide_runtime_policy` import 가능 여부 |

상태는 모든 check가 통과하면 `ready`, 하나라도 실패하면 `not_ready`다.

## Staging Smoke Checks

`scripts/staging_smoke.py`는 외부 HTTP 요청 기준으로 다음을 확인한다.

| Smoke | 의미 |
|---|---|
| `health` | `/health` 200, status ok, request_id header 확인 |
| `ready` | `/ready` 200, status ready 확인 |
| `public_chat` | public chat endpoint가 query-only 요청에 답변 반환 |
| `public_rejects_internal_options` | public endpoint가 `top_k` 같은 내부 옵션을 422로 거부 |
| `public_pharmacology_policy` | 반감기 의도 질문에서 pharmacology status가 응답에 포함 |
| `debug_chat` | debug endpoint는 내부 옵션 override 허용 |

## 실행 방법

API 서버 실행:

```bash
uv run uvicorn app.chat.api.main:app --host 127.0.0.1 --port 8000
```

다른 터미널에서 smoke 실행:

```bash
uv run python scripts/staging_smoke.py --base-url http://127.0.0.1:8000
```

## 설계 판단

- `/health`는 프로세스가 살아있는지 보는 가벼운 check다.
- `/ready`는 데이터, index, API key, runtime import처럼 실제 요청 처리에 필요한 의존성을 본다.
- smoke test는 내부 함수 호출이 아니라 HTTP 표면을 확인한다.
- public endpoint와 debug endpoint의 차이를 smoke에서 확인해 운영 표면이 실험 옵션에 오염되지 않도록 했다.

## 검증

- `uv run ruff check app/chat/api/readiness.py scripts/staging_smoke.py tests/chat/api/test_api.py tests/chat/api/test_readiness.py tests/chat/api/test_staging_smoke.py`: 통과
- `uv run pytest tests/chat/api/test_api.py tests/chat/api/test_readiness.py tests/chat/api/test_staging_smoke.py`: 20 passed
