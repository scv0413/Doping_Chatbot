# Doping Chatbot

KADA/WADA 도핑 규정, 금지약물, 현장 대응, 반감기 정보를 근거 기반으로 안내하는 선수·트레이너용 RAG 챗봇입니다.

이 프로젝트는 사용자를 도핑 규정 전문가로 만들기보다, 경기장과 의료 상황처럼 시간이 부족한 순간에 **위험한 행동을 피하고 공식 근거를 확인하도록 돕는 보조 도구**를 목표로 합니다.

> 공식 판정 도구가 아닙니다. 약물 사용, TUE, 시료채취 거부·지연 판단은 KADA/WADA 공식 자료와 담당 전문가 확인이 필요합니다.

## Portfolio Snapshot

- **Implementation baseline:** `4f45bf8` 이후 검증된 기능을 기준으로 동결
- **Regression tests:** `228 passed`
- **Local release gate:** 15 cases, `route_match`, `source_hit`, `term_hit`, `retrieval_quality`, `tool_contract` 모두 `1.0`
- **LangSmith:** retrieval 및 deterministic answer evaluation 완료
- **Safety:** retrieved context 기반 답변, 명시적 출처, 정보 부족 시 보류, 단정 방지, 대상자 톤, 안전 고지의 6-rule policy 적용

## Problem

도핑 교육에서는 홈페이지 검색을 안내하지만, 실제 현장에는 시간·언어·긴장이 동시에 작용합니다.

- 해외 경기 중 검사 통지와 응급 치료가 충돌하는 상황
- 새벽 혈액 시료 채취 요청에서 검사관 신분과 절차를 빠르게 확인해야 하는 상황
- 감기약, 비강 스프레이, 진통제의 제품명·성분명·투여경로를 확인해야 하는 상황
- 반감기 정보를 경기기간 복용 가능 여부로 잘못 해석할 위험

## Architecture

```text
PDF / manual / official source
  -> inspection -> preprocessing -> chunks + provenance metadata
  -> OpenAI embeddings + Chroma retrieval
  -> query rewrite + explicit-section rerank
  -> router
       -> rag_search_tool
       -> drug_search_tool
       -> pharmacology_info_tool
  -> LangGraph controlled tool plan (bounded retry)
  -> policy + deterministic formatter + optional LLM answer chain
  -> Gradio / FastAPI / FastMCP
  -> pytest + release gate + LangSmith evaluation
```

### Why separate the domains?

| Layer | Responsibility | Why it is separate |
|---|---|---|
| `retrieval` | Regulations, procedures, field guidance | Requires document provenance and citation quality |
| `drug_search` | Product/ingredient lookup | Product names and ingredient names do not behave like regulatory documents |
| `pharmacology` | Half-life and pharmacology reference | Must never be treated as a competition eligibility decision |
| `answer` / `policy` | Safe rendering and LLM constraints | Keeps safety rules testable apart from retrieval |
| `orchestration` | Router, pipeline, LangGraph, bounded agent plan | Separates intent, tool execution, retry, and exit rules |

### Controlled agent and MCP

The project does not use an unrestricted LLM agent. The router and runtime policy create a bounded tool plan:

```text
field/regulation -> rag_search_tool
product/ingredient -> drug_search_tool
drug + regulation -> drug_search_tool -> rag_search_tool
half-life substance -> drug_search_tool -> pharmacology_info_tool -> rag_search_tool
```

LangGraph allows only one retrieval retry, uses message trimming, and has an explicit exit node. MCP-compatible Pydantic tool contracts are exposed through FastMCP for `rag_search_tool`, `drug_search_tool`, and `pharmacology_info_tool`. The internal registry executor remains the default; the HTTP MCP executor is optional and falls back internally on transport failure.

## Source Quality and Provenance

- PDF layout is inspected before indexing: reading order, columns, table of contents, footer, and character quality are recorded.
- Broken OCR or low-quality pages are excluded rather than silently indexed.
- WADA ISTI 2023 English is the active ISTI source.
- Korean guidance is indexed only after project review. It is clearly labeled as non-official Korean guidance and cites the official English source page.
- Current reviewed ISTI Korean scope: Articles `5.3.5` through `5.4.5`, including notification, interpreter/third party, identity, signature, delay, and continuous observation.

A useful recent regression illustrates the approach: the query about delaying a Doping Control Station visit initially retrieved only broad field guidance. The relevant ISTI `5.4.4` chunk was 13th in vector similarity. When the query explicitly contained `Article 5.4.4`, the retriever now expands the candidate pool and prioritizes the matching document `section` only for that explicit reference. The release gate then returned all quality metrics at `1.0`.

## Repository Layout

```text
app/
  core/                     # settings, data paths
  preprocess/               # sources, PDF extraction, transform, OCR, manual loading
  chat/
    domain/                 # retrieval, drug_search, pharmacology, answer, policy
    orchestration/          # router, pipeline, LangGraph, controlled agent plan
    tools/                  # Pydantic/MCP-compatible tool contracts and registry
    interfaces/             # FastAPI, Gradio, FastMCP adapters
    evals/                  # LangSmith and local quality gates
    runtime.py              # shared public entrypoint
scripts/                    # refresh, smoke, release quality CLI
tests/                      # structure-mirrored regression tests
data/                       # raw, processed, Chroma indexes, operations (git ignored)
docs/                       # architecture, operations, evaluation decisions
local_archive/              # personal presentation and rehearsal materials (git ignored)
```

## Run Locally

### Environment

Python 3.12 and `uv` are used.

```bash
uv sync --extra dev
```

Create `.env` from `.env.example`.

```env
OPENAI_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=doping-chatbot
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

### Data and index

```bash
uv run python -m app.preprocess.transform.preprocess
uv run python -m app.preprocess.transform.chunker
uv run python -m app.chat.domain.retrieval.indexer
```

### API and UI

```bash
# FastAPI
uv run uvicorn app.chat.interfaces.api.main:app --host 127.0.0.1 --port 8000

# Gradio
uv run python -m app.chat.interfaces.ui.gradio_app --server-name 127.0.0.1 --server-port 7860
```

### MCP server

```bash
uv run python -m app.chat.interfaces.mcp.fastmcp_server
# streamable HTTP endpoint: http://127.0.0.1:8012/mcp
```

## Demo Queries

```text
도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?
도핑검사 통지서 서명을 거부하면 어떻게 돼?
치료나 통역 때문에 도핑관리소 도착을 미뤄도 돼? 혼자 움직여도 돼?
슈도에페드린 경기기간 중 먹어도 돼?
약물 반감기로 경기기간 복용 가능 여부를 판단해도 돼?
```

## Validation

```bash
# regression and static checks
uv run python -m pytest -q
uv run ruff check app tests scripts

# deterministic graph/tool release gate
uv run python scripts/release_quality_gate.py

# LangSmith experiments
uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 3
uv run python -m app.chat.evals.langsmith_answer_eval --top-k 3

# API staging smoke
uv run python scripts/staging_smoke.py --base-url http://127.0.0.1:8000
```

Latest verified baseline:

- `228 passed`
- release gate: 15 cases; all required metric averages `1.0`
- [LangSmith retrieval experiment](https://smith.langchain.com/o/2d4720fb-5dfa-4666-983e-680c70b9ab87/datasets/aabceefb-4dbf-412c-9252-753697fdfb61/compare?selectedSessions=9eec1299-4641-4f67-88ca-227aee233144)
- [LangSmith deterministic answer experiment](https://smith.langchain.com/o/2d4720fb-5dfa-4666-983e-680c70b9ab87/datasets/a7f204a4-bd4e-410c-90ac-61b2a4453de0/compare?selectedSessions=632f4b89-daff-465d-91e6-eba3fef27b0a)

## API and Operations

- Public endpoint: `POST /api/v1/chat-responses` accepts only `query`.
- Debug endpoint: `POST /api/v1/debug/chat-responses` allows `top_k`, `use_llm`, and engine overrides for evaluation.
- `/health` checks process health; `/ready` checks runtime/data/index readiness.
- Every API request receives an `X-Request-ID` and JSON structured logs.
- Docker runs as a non-root user and supports readiness/staging smoke checks.

## Known Limitations

- KADA drug search needs a production-level change-detection and rate-limit policy before public operation.
- Pharmacology coverage is intentionally limited to a curated MVP set; half-life never determines eligibility on its own.
- Only reviewed Korean guidance is indexable. More official sources and reviewed Korean sections are needed.
- Authentication, role-based access, rate limits, audit retention, and CI/CD deployment automation are operating-stage work.
- The chatbot is decision support, not legal, medical, or official anti-doping adjudication.

## What This Project Demonstrates

This is not just a PDF chatbot. It demonstrates how to build a high-risk RAG service through source quality controls, separated domain tools, constrained agent execution, explicit citations, policy-driven answers, local regression gates, LangSmith evaluation, and operational interfaces.
