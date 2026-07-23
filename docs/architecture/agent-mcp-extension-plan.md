# Agent and MCP Extension Plan

## 목적

현재 프로젝트는 RAG 챗봇으로 시작했지만, 최종 목표는 LLM이 단순히 텍스트만 생성하는 것이 아니라 필요한 도구를 선택해 실행하는 구조다.
다만 바로 복잡한 agent를 만들면 검색 품질, 답변 안전성, 운영 안정성이 흔들릴 수 있다.
따라서 이미 검증한 기능을 tool 단위로 감싸는 순서로 확장한다.

## 현재 안정화된 기능

현재 안정화된 기능은 다음과 같다.

- `run_chat`: 통합 runtime entrypoint
- `run_chat_graph`: LangGraph 기반 entrypoint
- retrieval: Chroma 기반 문서 검색
- drug_search: 제품명/성분명 기반 약물 조회
- pharmacology_info: 반감기와 약리 정보
- field_response: 현장 상황별 안전 행동 안내
- answer formatter / answer chain
- Runtime Policy

## 왜 MCP/Agent 전에 tool contract가 필요한가

Agent는 자유롭게 행동하는 구조가 아니라, 제한된 도구를 정확한 입력/출력 계약에 따라 호출하는 구조여야 한다.
도핑 도메인에서는 tool contract가 특히 중요하다.

- 어떤 입력을 받을 수 있는지 명확해야 한다.
- 어떤 출처를 반환하는지 추적 가능해야 한다.
- 답변이 부족할 때 모른다고 말할 수 있어야 한다.
- 약물 복용 가능 여부를 임의로 단정하지 않아야 한다.
- 실행 로그와 request_id를 남길 수 있어야 한다.

## 추천 Tool 목록

### 1. `rag_search_tool`

문서 근거 검색 전용 tool.

입력:

```json
{
  "query": "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
  "top_k": 3
}
```

출력:

```json
{
  "results": [
    {
      "chunk_id": "wada_isti_2021_ko_en:p23:c0",
      "source_id": "wada_isti_2021_ko_en",
      "page": 23,
      "text": "...",
      "score": 0.82
    }
  ]
}
```

주의:

- tool은 답변을 생성하지 않는다.
- 근거 chunk만 반환한다.
- 답변 생성은 answer layer에서 수행한다.

### 2. `drug_search_tool`

제품명/성분명 기반 약물 조회 tool.

입력:

```json
{
  "keyword": "타이레놀"
}
```

출력:

```json
{
  "query": "타이레놀",
  "results": [
    {
      "product_name": "...",
      "ingredient_name": "acetaminophen",
      "status": "...",
      "source_url": "https://kada.health.kr/result_drug"
    }
  ],
  "safety_note": "제품명과 성분명을 함께 확인해야 합니다."
}
```

주의:

- 제품명만으로 최종 복용 가능 여부를 단정하지 않는다.
- 성분명, 용량, 투여 경로, 경기기간 여부 확인을 유도한다.

### 3. `pharmacology_info_tool`

반감기와 약리 정보 안내 tool.

입력:

```json
{
  "ingredient": "pseudoephedrine"
}
```

출력:

```json
{
  "ingredient": "pseudoephedrine",
  "half_life_summary": "평균 반감기 정보",
  "caveats": [
    "개인차가 있습니다.",
    "도핑 가능/불가능 판정이 아닙니다.",
    "경기 일정과 복용 시간을 함께 확인해야 합니다."
  ],
  "source_type": "pharmacology_info"
}
```

주의:

- 경기 출전 가능 여부를 단정하지 않는다.
- 사용자가 안심하거나 경기 포기를 판단할 때 참고 정보로만 제공한다.

### 4. `field_response_tool`

현장 상황별 안전 행동 안내 tool.

입력:

```json
{
  "scenario": "injury_delay",
  "question": "부상 치료가 먼저 필요한데 도핑검사를 미뤄달라고 하면 거부로 보일 수 있어?"
}
```

출력:

```json
{
  "scenario": "injury_delay",
  "risk": "무단 이탈이나 충돌은 거부/회피로 오해될 수 있습니다.",
  "recommended_action": "검사관에게 치료 필요성을 알리고 동행/기록을 요청합니다.",
  "documentation": ["시간", "검사관 이름", "상황", "의료진 판단"]
}
```

주의:

- 검사관과 충돌하거나 현장을 무단 이탈하라고 안내하지 않는다.
- 불합리한 상황에서도 기록, 동행, 공식 확인을 우선한다.

### 5. `report_generation_tool`

상황 기록 또는 상담 요약 보고서 생성 tool.

입력:

```json
{
  "user_role": "trainer",
  "scenario": "night_blood_collection",
  "facts": ["새벽", "혈액 시료 요청", "통역 부재"]
}
```

출력:

```json
{
  "report_markdown": "...",
  "missing_information": ["검사관 이름", "통지 시간", "통역 요청 여부"]
}
```

주의:

- 법적 판단 문서가 아니라 상황 기록 보조 문서임을 명시한다.
- 사용자가 입력하지 않은 사실을 만들어내지 않는다.

## Agent Graph 추천 순서

### Phase 1. Tool wrapping only

기존 기능을 tool로 감싼다.
Agent가 자유롭게 reasoning하지 않고, route 결과에 따라 정해진 tool을 호출한다.

### Phase 2. One retry agentic graph

검색 결과가 비거나 retrieval_quality가 낮을 때만 query rewrite 후 1회 재검색한다.
무한 루프 방지를 위해 recursion limit과 retry_count를 둔다.

### Phase 3. Multi-tool synthesis

약물 질문에서 drug_search, pharmacology_info, RAG safety manual을 함께 호출한다.
답변은 formatter 또는 policy-aware answer chain이 생성한다.

### Phase 4. MCP server exposure

검증된 tool만 MCP server로 노출한다.
이때 tool별 input schema, output schema, error response, logging 기준을 고정한다.

## Guardrails

- recursion_limit 사용
- retry_count 최대 1회부터 시작
- message trimming 적용
- 추후 summarization node 추가
- tool output을 그대로 사용자에게 노출하지 않고 answer layer를 거친다
- 모든 factual claim은 citation 또는 source field를 갖는다
- 정보 부족 시 모른다고 답한다

## 포트폴리오에서 설명할 포인트

Agent 확장은 “LLM에게 마음대로 맡기는 것”이 아니다.
이미 평가된 retrieval, drug_search, pharmacology, field_response를 안전한 tool로 감싸고, LangGraph가 어떤 tool을 언제 호출할지 통제하는 구조다.

즉 이 프로젝트의 agentic 확장은 다음 순서로 간다.

1. RAG 품질 안정화
2. 답변 안전성 평가
3. Runtime Policy 고정
4. LangGraph로 실행 흐름 분리
5. 검증된 기능만 tool화
6. MCP로 외부 agent 환경에 노출

## 구현 반영 상태

현재 다음 항목은 구현되었다.

- `app/chat/tools/` 디렉토리 생성
- `RagSearchRequest`, `RagSearchResult`, `RagSearchToolOutput`, `ToolError` schema 정의
- `rag_search_tool` 구현
- `DrugSearchToolRequest`, `DrugSearchToolOutput` schema 정의
- `drug_search_tool` 구현
- tool 단위 pytest 작성
- 실제 Chroma index 기반 smoke 확인
- deterministic fake searcher 기반 drug_search_tool smoke 확인
- `PharmacologyInfoToolRequest`, `PharmacologyInfoToolOutput` schema 정의
- `pharmacology_info_tool` 구현
- pharmacology knowledge base 기반 local smoke 확인

## LangGraph 전환 반영 상태

현재 LangGraph retrieve node는 내부적으로 `rag_search_tool`을 호출한다. 또한 drug search node는 내부적으로 `drug_search_tool`을 호출하고, pharmacology node는 `pharmacology_info_tool`을 호출한다.

구조는 다음과 같다.

```text
rewritten_query
  -> RagSearchRequest
  -> rag_search_tool
  -> RagSearchToolOutput
  -> RetrievalMatch adapter
  -> answer layer

search_input
  -> DrugSearchToolRequest
  -> drug_search_tool
  -> DrugSearchToolOutput
  -> DrugSearchResult
  -> answer layer

search_input.query
  -> PharmacologyInfoToolRequest
  -> pharmacology_info_tool
  -> PharmacologyInfoToolOutput
  -> PharmacologyInfoResult
  -> answer layer
```

이 구조를 선택한 이유는 다음과 같다.

- graph 내부에 tool boundary를 도입한다.
- 기존 answer layer가 기대하는 `RetrievalMatch` 구조는 유지한다.
- state에 `rag_search_output`, `drug_search_tool_output`, `pharmacology_info_tool_output`을 남겨 이후 LangSmith tool trace/eval에 활용할 수 있다.
- 외부 동작은 유지하면서 MCP 확장 준비를 진행한다.

## 다음 구현 후보

1. LangSmith tool trace 비교
2. `rag_search_output`와 `drug_search_tool_output` 기반 tool eval 확장
3. MCP server exposure 전 input/output schema 안정화
4. LangSmith tool eval에 pharmacology tool contract 추가
5. `field_response_tool` 구현


## MCP-compatible Registry 반영 상태

실제 MCP server adapter를 붙이기 전 단계로, 내부 tool을 MCP-compatible schema와 executor registry로 노출했다.

구현 파일:

- `app/chat/tools/mcp_schema.py`
- `app/chat/tools/mcp_registry.py`
- `tests/chat/tools/test_mcp_registry.py`

제공 기능:

- `list_mcp_tools()`
  - `rag_search_tool`, `drug_search_tool`, `pharmacology_info_tool`의 name, description, inputSchema 반환
- `get_mcp_tool(name)`
  - 단일 tool definition 반환
- `execute_mcp_tool(name, arguments, dependencies)`
  - MCP adapter가 넘겨줄 JSON arguments를 Pydantic request schema로 검증한 뒤 내부 tool 실행

이 구조를 선택한 이유는 다음과 같다.

- MCP server 구현체에 종속되지 않고 tool contract를 먼저 안정화한다.
- Pydantic schema를 MCP `inputSchema`로 재사용한다.
- 기존 LangGraph 내부 tool과 외부 MCP 노출 tool이 같은 request/output contract를 공유한다.
- 테스트에서는 fake dependency를 주입해 네트워크/API key 없이 tool contract를 검증할 수 있다.

## Controlled Agent Tool Plan 반영 상태

자유형 LLM agent 대신, router와 intent 규칙을 기준으로 필요한 tool만 호출하는 deterministic agent tool plan을 추가했다.

구현 파일:

- `app/chat/agent/tool_agent.py`
- `tests/chat/graph/test_agent_tool_plan.py`

호출 흐름:

```text
query
  -> normalize_pipeline_input
  -> route_question
  -> if drug route: drug_search_tool
  -> if pharmacology intent: pharmacology_info_tool
  -> if retrieval route: rag_search_tool
  -> AgentToolRunResult(tool call trace)
```

검증된 예:

| 질문 유형 | route | 호출 tool |
|---|---|---|
| 검사관 신분 확인 | `rag` | `rag_search_tool` |
| 타이레놀 복용 질문 | `drug_search` | `drug_search_tool` |
| 슈도에페드린 반감기 질문 | `drug_search_with_rag` | `drug_search_tool` -> `pharmacology_info_tool` -> `rag_search_tool` |

이 단계의 핵심은 “agent가 스스로 아무 tool이나 고르는 것”이 아니라, 이미 검증한 router/policy 기준으로 필요한 tool만 호출하고 모든 tool input/output을 trace로 남기는 것이다.

## 다음 MCP 구현 후보

1. 실제 MCP server adapter 추가
2. `list_tools`에서 `list_mcp_tools()` 반환
3. `call_tool`에서 `execute_mcp_tool()` 호출
4. LangSmith tool trace/eval에 MCP adapter 호출 결과 연결
5. report generation, notification 같은 action tool은 인증/권한 설계 이후 추가


## MCP Server Adapter Core 반영 상태

MCP Python SDK 의존성을 바로 추가하지 않고, 먼저 SDK-free adapter core를 구현했다.

구현 파일:

- `app/chat/interfaces/mcp/server_adapter.py`
- `tests/chat/tools/test_mcp_server_adapter.py`

제공 기능:

- `list_tools()`
  - 내부 `list_mcp_tools()` 결과를 MCP list tools response 형태로 감싼다.
- `call_tool(name, arguments, dependencies)`
  - 내부 `execute_mcp_tool()`을 호출한다.
  - 정상 output은 `structuredContent`와 text content에 함께 담는다.
  - tool runtime error가 있으면 `isError=true`로 표시한다.
  - validation error나 unknown tool은 `mcp_adapter` stage error로 반환한다.

이 구조를 선택한 이유:

- MCP SDK/transport 버전 변화와 내부 tool contract를 분리한다.
- 외부 의존성을 추가하지 않고 adapter 동작을 테스트할 수 있다.
- 다음 단계에서 실제 MCP SDK server는 `list_tools()`와 `call_tool()`만 연결하면 된다.

현재 범위는 MCP protocol transport가 아니라 server adapter core다. 즉 stdio/SSE transport를 실제로 열지는 않는다.


## FastMCP Server 반영 상태

공식 MCP Python SDK v1.x의 `FastMCP`를 사용해 실제 MCP server entrypoint를 추가했다.

구현 파일:

- `app/chat/interfaces/mcp/fastmcp_server.py`
- `tests/chat/tools/test_fastmcp_server.py`

구성:

- server name: `doping-chatbot-mcp`
- transport: `streamable-http`
- path: `/mcp`
- local port: `8012`
- FastAPI 기본 포트 `8000`과 충돌하지 않도록 MCP 서버 포트를 분리
- `stateless_http=True`
- `json_response=True`

실행:

```bash
uv run python -m app.chat.interfaces.mcp.fastmcp_server
```

노출 tool:

- `rag_search_tool`
- `drug_search_tool`
- `pharmacology_info_tool`

검증 중 발견한 오류:

- `FastMCP.list_tools()`는 시그니처상 일반 메서드처럼 보였지만 실제로 coroutine을 반환했다.
- 테스트를 `asyncio.run(server.list_tools())`로 수정했다.
- 전역 `python`에서는 `mcp` import가 실패했다. 프로젝트 실행 기준을 `uv run`으로 통일해 해결했다.

실제 연결 검증:

```bash
uv run python -m app.chat.interfaces.mcp.fastmcp_server
uv run python scripts/mcp_smoke.py --call-pharmacology
```

검증 결과:

- `rag_search_tool`, `drug_search_tool`, `pharmacology_info_tool`이 모두 MCP client에서 조회됐다.
- `pharmacology_info_tool` 호출 결과가 structured content로 반환됐다.

이 단계부터는 실제 MCP client/inspector가 연결할 수 있는 server entrypoint가 생겼다.


## LangSmith MCP Eval 반영 상태

MCP server entrypoint를 실제 LangSmith eval target에 연결했다.

구현 파일:

- `app/chat/evals/langsmith_mcp_eval.py`
- `tests/chat/evals/test_langsmith_mcp_eval.py`

평가 흐름:

1. LangSmith dataset case의 `query`를 읽는다.
2. local router로 `rag`, `drug_search`, `drug_search_with_rag`를 결정한다.
3. route에 따라 MCP client가 streamable HTTP endpoint를 통해 tool을 호출한다.
4. MCP structured content를 LangSmith evaluator가 읽을 수 있는 field로 정규화한다.
5. 기존 retrieval evaluator와 `tool_contract_evaluator`를 재사용한다.
6. MCP 전용 `mcp_connection_evaluator`로 tool 목록과 연결 오류를 확인한다.

실행:

```bash
uv run python -m app.chat.interfaces.mcp.fastmcp_server
uv run python -m app.chat.evals.langsmith_mcp_eval --top-k 3 --skip-dataset-upload
```

검증 결과:

- local MCP target smoke에서 `mcp_connection_score=1`, `tool_contract_score=1` 확인
- 실제 LangSmith experiment 생성 확인: `mcp-tool-top3-rewrite-True-94c6129c`
- 10개 case 실행 완료

의미:

Graph 내부 tool contract 평가에서 한 단계 더 나아가, 실제 MCP transport를 경유해도 tool 호출 계약과 retrieval 품질 평가가 유지되는지 확인할 수 있게 됐다.


## LangGraph Node Tool Executor 전환

LangGraph node가 개별 tool wrapper를 직접 호출하던 구조에서 MCP registry style executor를 경유하는 구조로 전환했다.

변경 전:

- `build_drug_search_node` -> `run_drug_search_tool()` 직접 호출
- `build_pharmacology_node` -> `run_pharmacology_info_tool()` 직접 호출
- `build_retrieve_node` -> `run_rag_search_tool()` 직접 호출

변경 후:

- graph node -> `run_graph_tool()` -> `ChatGraphDependencies.tool_executor()` -> `execute_mcp_tool()`
- tool 이름과 JSON arguments 기반으로 실행
- 출력은 다시 `DrugSearchToolOutput`, `PharmacologyInfoToolOutput`, `RagSearchToolOutput`으로 validate

이 구조의 의미:

- graph node는 개별 서비스 구현보다 tool contract에 의존한다.
- 내부 registry executor와 외부 MCP executor를 같은 contract로 비교하거나 교체할 수 있다.
- 기존 `run_chat_graph()` public API와 사용자 결과는 유지된다.
- retry, answer, state 변환 구조는 그대로 보존했다.

검증:

```bash
uv run pytest tests/chat/graph
uv run pytest
```

결과:

- graph 테스트: 13 passed
- 전체 테스트: 164 passed

이 단계는 완전한 외부 MCP graph가 아니라 1차 점진 전환이다. 실제 운영에서 모든 graph node가 HTTP MCP server를 호출하도록 바꾸는 것은 latency, failure handling, timeout, retry 정책을 추가로 확정한 뒤 진행한다.


## MCP HTTP Tool Executor 옵션

Graph 기본 실행은 내부 registry executor를 유지하되, 실제 MCP streamable HTTP server를 경유하는 executor 옵션을 추가했다.

구현 파일:

- `app/chat/interfaces/mcp/client_executor.py`
- `tests/chat/tools/test_mcp_client_executor.py`

사용 예:

```python
from app.chat.orchestration.graph.graph import run_chat_graph
from app.chat.interfaces.mcp.client_executor import MCPHTTPToolExecutor

result = run_chat_graph(
    "S0 비승인약물이 뭐야?",
    top_k=3,
    use_llm=False,
    tool_executor=MCPHTTPToolExecutor(),
)
```

실행 전제:

```bash
uv run python -m app.chat.interfaces.mcp.fastmcp_server
```

검증 결과:

- route: `rag`
- `rag_tool_name`: `rag_search_tool`
- `match_count`: 3
- `errors`: `[]`

주의:

`MCPHTTPToolExecutor`는 현재 동기 graph runner에 맞춘 sync wrapper다. 이미 실행 중인 event loop 안에서는 사용하지 않도록 guard를 둔다. FastAPI async path에서 외부 MCP executor를 운영 기본값으로 쓰려면 async graph runner 또는 thread/offload 정책을 별도로 설계해야 한다.


## MCP HTTP Timeout Retry Fallback 정책

외부 MCP server 호출은 네트워크, 프로세스, endpoint 상태에 영향을 받는다. 따라서 graph가 외부 MCP transport에만 의존하면 MCP server 장애가 곧 chatbot 장애로 이어질 수 있다.

정책:

- `timeout_seconds`: MCP tool call 최대 대기 시간
- `max_attempts`: 실패 시 재시도 횟수
- `fallback_executor`: 모든 시도가 실패하면 내부 registry executor로 복구
- 기본 fallback은 `execute_mcp_tool`
- fallback을 끄고 싶으면 `fallback_executor=None`

예시:

```python
from app.chat.orchestration.graph.graph import run_chat_graph
from app.chat.interfaces.mcp.client_executor import MCPHTTPToolExecutor

result = run_chat_graph(
    "S0 비승인약물이 뭐야?",
    top_k=3,
    use_llm=False,
    tool_executor=MCPHTTPToolExecutor(
        timeout_seconds=5,
        max_attempts=2,
    ),
)
```

장애 검증:

- 없는 MCP endpoint `http://127.0.0.1:9999/mcp`로 실행
- 내부 registry fallback으로 `match_count=3`, `errors=[]` 확인

정상 검증:

- 실제 MCP endpoint `http://127.0.0.1:8012/mcp`로 실행
- `rag_search_tool`, `match_count=3`, `errors=[]` 확인

운영 판단:

- API/Gradio 기본값은 내부 registry executor 유지
- 외부 MCP executor는 실험, 외부 agent 연동, MCP transport 검증용 옵션
- async API path에서 sync `MCPHTTPToolExecutor`를 직접 쓰지 않도록 running event loop guard 유지

## Controlled Agent Plan in Graph State

The graph now records a deterministic `AgentToolPlan` in a dedicated `plan` node after route classification. This is the explicit bridge between the previously standalone controlled tool planner and the runtime LangGraph execution path.

- plan order is decided before any tool call;
- `planned_tool_names` is retained in internal runtime/trace output;
- public API and Gradio do not expose implementation metadata;
- the bounded one-retry retrieval policy remains unchanged;
- `DEFAULT_RECURSION_LIMIT` is `12`, which covers the longest valid plan path plus one retry while retaining a hard execution cap.
