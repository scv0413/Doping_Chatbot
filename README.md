# Doping Chatbot

KADA/WADA 도핑 관련 규정, 금지약물, 현장 대응 시나리오, 반감기/약리 정보를 근거 기반으로 검색하고 답변하는 RAG 챗봇 프로젝트입니다.

목표 사용자는 엘리트 선수와 트레이너입니다. 도핑 교육 내용을 기억하는 것에만 의존하지 않고, 실제 경기장/응급상황/약물 복용 전 확인 상황에서 빠르게 참고할 수 있는 보조 도구를 목표로 설계했습니다.

> 이 프로젝트는 공식 판정 도구가 아닙니다. 약물 사용 가능 여부, TUE, 시료채취 절차, 검사 거부/지연 판단은 반드시 KADA/WADA 공식 자료와 담당 전문가 확인이 필요합니다.

## 주요 기능

- PDF/manual 기반 RAG 검색
- KADA 약물검색 성격의 drug search 계층
- 슈도에페드린 등 일부 성분의 반감기/약리 참고 정보 계층
- 질문 intent router
- deterministic formatter와 LangChain OpenAI 기반 answer chain
- LangGraph 기반 실행 흐름
- LangSmith retrieval/tool/answer/field/half-life eval
- Gradio MVP UI
- FastAPI REST API
- `/health`, `/ready`, request_id, JSON structured logging
- Docker non-root runtime, Docker build CI 검증

## Architecture

```text
app/
  preprocess/             # PDF/manual source 전처리, page JSONL 생성, chunk 생성
  chat/
    retrieval/            # LangChain OpenAI embeddings + LangChain Chroma 검색
    drug_search/          # KADA 약물검색 client/mock/formatter
    pharmacology/         # 반감기와 약리정보 참고 계층
    router/               # 질문 intent route 결정
    answer/               # deterministic formatter + LangChain ChatOpenAI answer chain
    policy/               # 6 rules, safety caveat, runtime policy
    graph/                # LangGraph 실행 흐름과 deterministic tool plan
    tools/                # rag/drug/pharmacology tool request/output contract
    runtime.py            # Gradio/FastAPI 공통 entrypoint
    api/                  # FastAPI, readiness, error response, JSON logging
    ui/                   # Gradio MVP
    evals/                # LangSmith/retrieval/answer/half-life/field eval
    docs/                 # 구현 판단, 운영, 평가 문서
scripts/
  staging_smoke.py        # HTTP 기준 staging smoke 검증
tests/                    # unit/integration/artifact tests
data/                     # raw/processed/indexes, git 제외
logs/                     # 작업 과정 기록, git 제외
local_archive/            # 발표용 HTML/학습 자료 보관, git 제외
```

## Environment

Python 3.12와 `uv`를 사용합니다.

```bash
uv sync --extra dev
```

`.env.example`을 기준으로 `.env`를 작성합니다.

필수:

```env
OPENAI_API_KEY=...
```

선택:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=doping-chatbot
```

기본 모델:

```env
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_COLLECTION_NAME=doping_chunks_openai_small
```

## Data Pipeline

전처리:

```bash
uv run python -m app.preprocess.transform.preprocess
uv run python -m app.preprocess.transform.chunker
```

색인:

```bash
uv run python -m app.chat.retrieval.indexer

Source 변경 audit 및 안전한 전체 재색인:

```bash
uv run python scripts/data_refresh.py
# 검토 완료 후에만:
uv run python scripts/data_refresh.py --apply
```
```

검색 확인:

```bash
uv run python -m app.chat.retrieval.retriever "슈도에페드린 경기기간" --top-k 3
uv run python -m app.chat.retrieval.retrieval_inspector
```

## Run Locally

API:

```bash
uv run uvicorn app.chat.api.main:app --host 127.0.0.1 --port 8000
```

Gradio:

```bash
uv run python -m app.chat.ui.gradio_app --server-name 127.0.0.1 --server-port 7860
```

Runtime inspector:

```bash
uv run python -m app.chat.runtime_inspector "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?" --no-llm --engine graph --top-k 3
```

## API

Public endpoint는 사용자 입력을 단순하게 유지하기 위해 `query`만 받습니다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat-responses \
  -H 'Content-Type: application/json' \
  -d '{"query":"새벽에 혈액 시료 채취를 요청받으면 어떻게 대응해야 해?"}'
```

개발/평가용 옵션 override는 debug endpoint에서만 허용합니다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/debug/chat-responses \
  -H 'Content-Type: application/json' \
  -d '{"query":"S0 비승인약물이 뭐야?","top_k":3,"use_llm":false,"engine":"graph"}'
```

## MCP Server

FastMCP 기반 MCP server entrypoint를 제공합니다. 기본 transport는 streamable HTTP이며 MCP endpoint는 `/mcp`입니다. FastAPI 기본 포트와 충돌하지 않도록 로컬 기본 포트는 `8012`를 사용합니다.

```bash
uv run python -m app.chat.mcp.fastmcp_server
```

MCP Inspector 또는 MCP client에서 다음 URL로 연결합니다.

```text
http://127.0.0.1:8012/mcp
```

노출 tool:

- `rag_search_tool`
- `drug_search_tool`
- `pharmacology_info_tool`

별도 터미널에서 client smoke 검증:

```bash
uv run python scripts/mcp_smoke.py --call-pharmacology
```

검증 기준:

- `missing_tools`가 빈 배열이어야 한다.
- `ok`가 `true`여야 한다.
- `pharmacology_call.structured_content.tool_name`이 `pharmacology_info_tool`이어야 한다.

LangSmith MCP tool eval 실행:

```bash
uv run python -m app.chat.evals.langsmith_mcp_eval --top-k 3 --skip-dataset-upload
```

이 명령은 실행 중인 MCP endpoint를 통해 tool을 호출하고, LangSmith에 `mcp_connection`, `tool_contract`, retrieval 품질 지표를 함께 기록합니다.

## Docker

Build:

```bash
docker build -t doping-chatbot-api:local .
```

Run with local data/env:

```bash
docker compose up --build api
```

Container는 non-root user로 실행됩니다. `/ready`는 data/index/API key가 준비되어야 `ready`가 됩니다.

## Validation

기본 검증:

```bash
uv run ruff check app tests scripts
uv run pytest
```

Staging smoke:

```bash
uv run python scripts/staging_smoke.py --base-url http://127.0.0.1:8000

Release quality gate (data/index가 준비된 staging 또는 release 후보 환경):

```bash
uv run python scripts/release_quality_gate.py
```
```

LangSmith retrieval/tool eval:

```bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3
```

Docker artifact 검증:

```bash
uv run pytest tests/test_docker_artifacts.py
```

최근 로컬 검증 기준:

- `uv run ruff check app tests scripts`: pass
- `uv run pytest`: 187 passed, 1 dependency warning
- Docker build: pass
- Docker container non-root: pass, user id `999`
- Docker `/health`: pass
- Docker `/ready`: JSON shape pass
- LangSmith tool eval: `tool_contract`, `route_match`, `source_hit`, `term_hit`, `retrieval_quality` 평균 1.0

## Design Decisions

- UI/API는 내부 구현을 모르고 `run_chat(ChatRequest)`만 호출합니다.
- public API와 Gradio는 `query`만 받습니다. `top_k`, `engine`, `use_llm`은 Runtime Policy가 결정합니다.
- debug API, runtime inspector, LangSmith eval runner에서만 내부 옵션을 명시할 수 있습니다.
- 최종 답변용 domain result와 LangSmith/tool trace용 tool output을 둘 다 graph state에 남깁니다.
- `/health`는 process health, `/ready`는 data/index/runtime readiness를 확인합니다.
- 기본 graph 실행은 내부 MCP-compatible registry executor를 사용합니다. 외부 MCP HTTP executor는 별도 server 연동과 transport 검증용 옵션이며, 장애 시 내부 executor로 fallback합니다.
- CI Docker 검증은 secret/data가 없으므로 `/ready`의 JSON shape를 확인하고, 실제 staging smoke는 `ready`까지 요구합니다.

## Known Limitations

- 일부 WADA ISTI 한국어 PDF는 텍스트 추출 품질 문제로 OCR/대체 데이터 보강이 필요합니다.
- KADA 약물검색은 실제 운영 수준의 안정화, rate limit, 변경 감지 전략이 추가로 필요합니다.
- 반감기/약리정보 reference는 MVP 범위의 일부 성분만 포함합니다.
- 챗봇 답변은 법적/의학적 판단을 대체하지 않습니다.
- 인증, 권한, rate limit은 향후 운영 단계에서 추가해야 합니다.

## Roadmap

1. 제출/시연용 문서와 README 유지보수
2. MCP tool wrapper로 `rag_search_tool`, `drug_search_tool`, `pharmacology_info_tool` 노출
3. agentic graph에서 tool 선택/재시도 정책 고도화
4. 사용자 권한, rate limit, audit logging 설계
5. OCR/추가 공식 데이터 source 보강
6. CI/CD 배포 자동화

## Portfolio Notes

발표용 HTML과 리허설 자료는 git에 올리지 않고 `local_archive/portfolio/`에 보관합니다. 구현과 직접 관련된 설계/운영 문서는 `app/chat/docs/`에 남깁니다.
