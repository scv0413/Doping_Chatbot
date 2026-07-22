# LangSmith Tool Trace and Eval Plan

## 목적

LangGraph retrieve node가 `rag_search_tool`을 호출하도록 전환된 뒤, 검색 품질이 유지되는지와 tool contract가 지켜지는지를 평가한다.

기존 graph retrieval eval은 최종 `retrieval_matches`만 평가했다.
이번 tool eval은 그보다 한 단계 안쪽인 `rag_search_output`도 확인한다.

## 평가 대상

새 평가 target:

```text
app/chat/evals/langsmith_tool_eval.py
```

핵심 함수:

- `build_graph_tool_target`
- `tool_contract_evaluator`
- `run_langsmith_graph_tool_eval`

## 출력 구조

`build_graph_tool_target`은 기존 retrieval eval output에 다음 tool 관련 값을 추가한다.

- `tool_name`
- `tool_query`
- `tool_top_k`
- `tool_result_count`
- `tool_errors`
- `tool_source_ids`
- `tool_chunk_ids`

기존 evaluator와 호환되도록 다음 값도 유지한다.

- `actual_route`
- `source_ids`
- `chunk_ids`
- `retrieved_text`
- `context_chars`
- `retrieval_attempts`
- `error`

## Tool Contract Evaluator

`tool_contract_evaluator`는 다음을 확인한다.

### RAG 또는 drug_search_with_rag route

- `tool_name == "rag_search_tool"`
- tool result 수와 final chunk 수가 같다.
- `tool_chunk_ids == chunk_ids`
- tool error가 없다.

### drug_search only route

- RAG tool이 호출되지 않아야 한다.
- `tool_name is None`
- `tool_result_count == 0`

## 로컬 검증 결과

LangSmith 업로드 없이 `DEFAULT_CASES` 10개에 대해 로컬 target/evaluator를 실행했다.

결과:

- avg_tool_contract: 1.0
- avg_retrieval_quality: 1.0

케이스별 결과:

| Case | Route | Tool | Tool Contract | Retrieval Quality |
|---|---|---|---:|---:|
| definition_s0 | rag | rag_search_tool | 1.0 | 1.0 |
| drug_tylenol | drug_search | None | 1.0 | 1.0 |
| drug_pseudoephedrine | drug_search_with_rag | rag_search_tool | 1.0 | 1.0 |
| procedure_tue | rag | rag_search_tool | 1.0 | 1.0 |
| field_dco_identity | rag | rag_search_tool | 1.0 | 1.0 |
| field_night_blood | rag | rag_search_tool | 1.0 | 1.0 |
| field_injury_delay | rag | rag_search_tool | 1.0 | 1.0 |
| drug_nasal_spray | drug_search_with_rag | rag_search_tool | 1.0 | 1.0 |
| field_leave_station | rag | rag_search_tool | 1.0 | 1.0 |
| drug_half_life | rag | rag_search_tool | 1.0 | 1.0 |

## LangSmith 실행 명령

외부 LangSmith에 dataset과 run 결과가 업로드되므로 실행 전 명시적 승인이 필요하다.

```bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3 --skip-dataset-upload
```

처음 dataset을 생성하거나 최신 예시를 업로드하려면 다음을 사용한다.

```bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3
```

## 해석

이번 결과는 LangGraph retrieve node가 `rag_search_tool`을 거치도록 변경된 뒤에도 기존 retrieval 품질이 유지되며, tool output과 최종 retrieval output이 일치한다는 근거다.

이는 MCP 노출 전 중요한 기준선이다.
MCP로 tool을 노출하기 전에 tool input/output contract가 내부 graph에서 먼저 안정적으로 검증되어야 하기 때문이다.
