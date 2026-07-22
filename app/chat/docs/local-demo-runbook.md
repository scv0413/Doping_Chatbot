# Local Demo Runbook

## 목적

포트폴리오 시연 또는 로컬 검증 시 어떤 순서로 실행하면 되는지 정리한다.

## 1. 환경 준비

```bash
uv sync --extra dev
```

`.env` 확인:

```env
OPENAI_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=doping-chatbot
```

## 2. 데이터 준비

원본 PDF/manual source가 바뀌었을 때만 실행한다.

```bash
uv run python -m app.preprocess.preprocess
uv run python -m app.preprocess.chunker
uv run python -m app.chat.retrieval.indexer
```

이미 `data/processed`와 `data/indexes`가 준비되어 있으면 생략할 수 있다.

## 3. API 시연

서버 실행:

```bash
uv run uvicorn app.chat.api.main:app --host 127.0.0.1 --port 8000
```

확인:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Public chat:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat-responses \
  -H 'Content-Type: application/json' \
  -d '{"query":"도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?"}'
```

반감기/약리 질문:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat-responses \
  -H 'Content-Type: application/json' \
  -d '{"query":"슈도에페드린 반감기가 얼마나 돼?"}'
```

## 4. Gradio 시연

```bash
uv run python -m app.chat.ui.gradio_app --server-name 127.0.0.1 --server-port 7860
```

브라우저에서 접속:

```text
http://127.0.0.1:7860
```

추천 질문:

- `도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?`
- `새벽에 혈액 시료 채취를 요청받으면 어떻게 대응해야 해?`
- `타이레놀 먹어도 돼?`
- `경기기간 중 코감기약을 비강 스프레이로 써도 돼?`
- `슈도에페드린 반감기가 얼마나 돼?`

## 5. Docker 시연

Build:

```bash
docker build -t doping-chatbot-api:local .
```

Compose 실행:

```bash
docker compose up --build api
```

확인:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

컨테이너 user 확인:

```bash
docker exec doping-chatbot-api id -u
```

`0`이 아니면 non-root 실행이다.

## 6. Staging Smoke

API가 실행 중인 상태에서 실행한다.

```bash
uv run python scripts/staging_smoke.py --base-url http://127.0.0.1:8000
```

확인 항목:

- `/health`
- `/ready`
- public chat
- public endpoint의 내부 옵션 거부
- pharmacology policy 응답
- debug endpoint

## 7. LangSmith Eval

Retrieval/tool eval:

```bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3
```

Dataset 업로드를 생략하고 run만 확인:

```bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3 --skip-dataset-upload
```

확인 지표:

- `tool_contract`
- `route_match`
- `source_hit`
- `term_hit`
- `retrieval_quality`

특히 `drug_half_life` 케이스에서 route는 `rag`여도 `pharmacology_tool_name=pharmacology_info_tool`이 보여야 한다.

## 8. MCP Server 시연

FastMCP server 실행:

```bash
uv run python -m app.chat.mcp.fastmcp_server
```

기본 연결 URL:

```text
http://127.0.0.1:8012/mcp
```

MCP Inspector를 사용할 경우 별도 터미널에서 inspector를 실행하고 위 URL로 연결한다.

노출 tool:

- `rag_search_tool`
- `drug_search_tool`
- `pharmacology_info_tool`

MCP client smoke 검증:

```bash
uv run python scripts/mcp_smoke.py --call-pharmacology
```

성공 기준:

- `tool_names`에 세 tool이 모두 있어야 한다.
- `missing_tools`가 비어 있어야 한다.
- `ok`가 `true`여야 한다.
- pharmacology tool 호출 결과가 structured content로 반환되어야 한다.

LangSmith MCP tool eval:

```bash
uv run python -m app.chat.evals.langsmith_mcp_eval --top-k 3 --skip-dataset-upload
```

성공 기준:

- LangSmith experiment 링크가 출력되어야 한다.
- 10개 retrieval eval case가 실행되어야 한다.
- `mcp_connection`과 `tool_contract`가 주요 확인 지표다.

운영 기본값은 graph 내부의 MCP-compatible registry executor다. 외부 MCP HTTP executor는 MCP transport를 실제로 검증하거나 외부 agent와 연동할 때만 사용한다. MCP server가 일시적으로 응답하지 않으면 HTTP executor는 설정된 timeout/retry 뒤 내부 executor로 fallback한다.

## 9. 최종 검증

```bash
uv run ruff check app tests scripts
uv run pytest
```

현재 기준:

- full tests: 181 passed, 1 dependency warning
- ruff: pass
