# LangGraph Node and Tool Structure

## 목적

LangGraph는 사용자 질문을 여러 node로 나누어 처리한다. 현재 graph는 복잡한 agent가 아니라 기존 chat pipeline과 동일한 동작을 graph 구조로 표현하는 1차 구조다. 이후 MCP tool, agentic retry, LangSmith trace/eval을 붙이기 위해 node와 tool output의 책임을 분리했다.

## Node 책임

| Node | 역할 | 주요 output |
|---|---|---|
| `route` | 질문을 표준 입력으로 정규화하고 route 결정 | `search_input`, `decision` |
| `drug_search` | 약물명/성분명 기반 KADA 약물조회 tool 호출 | `drug_result`, `drug_search_tool_output` |
| `pharmacology` | 반감기/대사/배출 의도일 때 약리정보 tool 호출 | `pharmacology_result`, `pharmacology_info_tool_output` |
| `rewrite` | RAG 검색용 query 구성과 query rewrite 수행 | `retrieval_query`, `rewritten_query` |
| `retrieve` | RAG search tool 호출 및 검색 품질 재시도 판단 | `rag_search_output`, `retrieval_matches`, `retrieval_retry_reason` |
| `retry_rewrite` | 검색 결과가 부족할 때 1회 보강 query 생성 | `rewritten_query` |
| `answer` | deterministic formatter 또는 LLM chain으로 답변 생성 | `answer` |
| `exit` | answer 누락 시 최종 방어 응답 생성 | `answer`, `errors` |

## Tool Output을 State에 남기는 이유

최종 답변만 남기면 어떤 도구가 어떤 입력으로 호출됐는지 검증하기 어렵다. 그래서 graph state에는 최종 domain result와 tool output을 둘 다 남긴다.

- `drug_result`: 답변 생성에 쓰는 domain result
- `drug_search_tool_output`: tool contract, trace, error 확인에 쓰는 실행 흔적
- `pharmacology_result`: 답변 생성에 쓰는 domain result
- `pharmacology_info_tool_output`: 반감기 tool 호출 여부와 오류 확인에 쓰는 실행 흔적
- `retrieval_matches`: 답변 생성에 쓰는 검색 결과
- `rag_search_output`: RAG tool 호출 입력/결과/error 검증에 쓰는 실행 흔적

## Error Handling 원칙

각 tool은 자체 `ToolError`를 반환한다. graph node는 이를 `PipelineError`로 변환해 `errors`에 누적한다. 이 구조를 유지하면 API, Gradio, LangSmith eval에서 같은 오류 형식을 볼 수 있다.

이번 정리에서 `state_errors`, `append_tool_errors`, `build_*_tool_request` helper를 둔 이유는 다음과 같다.

- node마다 `errors = list(state.get("errors", []))`를 반복하지 않는다.
- tool request 생성 로직을 node 본문에서 분리한다.
- tool error를 pipeline error로 바꾸는 경로를 하나로 모은다.
- 이후 request_id, auth, user role, tool timeout 같은 운영 필드가 추가되어도 helper만 확장하면 된다.

## 현재 구조의 한계

- 아직 복잡한 multi-agent graph는 아니다.
- retry는 RAG 검색 부족 시 1회만 수행한다.
- token trimming과 summary node는 기본 방어 설계만 잡혀 있고, 긴 대화 운영 단계에서 추가 고도화 대상이다.

## 다음 확장 포인트

1. LangSmith에서 node/tool trace를 기준으로 failure case를 누적한다.
2. `rag_search_tool`, `drug_search_tool`, `pharmacology_info_tool`을 MCP tool schema와 맞춰 외부 agent가 호출할 수 있게 한다.
3. API/UI는 내부 graph 구조를 몰라도 `run_chat_graph` 또는 통합 `run_chat` entrypoint만 호출하게 유지한다.
