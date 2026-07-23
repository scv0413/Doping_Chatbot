# LangSmith Tool Trace and Eval Plan

## 목적

LangGraph retrieve node가 `rag_search_tool`을 호출하고, drug search node가 `drug_search_tool`을 호출하며, 반감기/약리 의도 질문에서 `pharmacology_info_tool`을 호출하도록 전환된 뒤, 검색/약물조회/약리정보 품질이 유지되는지와 tool contract가 지켜지는지를 평가한다.

기존 graph retrieval eval은 최종 `retrieval_matches`만 평가했다.
이번 tool eval은 그보다 한 단계 안쪽인 `rag_search_output`, `drug_search_tool_output`, `pharmacology_info_tool_output`도 확인한다.

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

- `rag_tool_name`
- `rag_tool_query`
- `rag_tool_top_k`
- `rag_tool_result_count`
- `rag_tool_errors`
- `rag_tool_source_ids`
- `rag_tool_chunk_ids`
- `drug_tool_name`
- `drug_tool_query`
- `drug_tool_status`
- `drug_tool_matched_substances`
- `drug_tool_prohibited_categories`
- `drug_tool_errors`
- `pharmacology_tool_name`
- `pharmacology_tool_query`
- `pharmacology_tool_status`
- `pharmacology_tool_substance_name`
- `pharmacology_tool_matched_terms`
- `pharmacology_tool_has_half_life`
- `pharmacology_tool_errors`

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

### rag route

- `rag_tool_name == "rag_search_tool"`
- RAG tool result 수와 final chunk 수가 같다.
- `rag_tool_chunk_ids == chunk_ids`
- RAG tool error가 없다.
- Drug tool은 호출되지 않아야 한다.

### drug_search route

- `drug_tool_name == "drug_search_tool"`
- `drug_tool_status`가 존재한다.
- Drug tool error가 없다.
- RAG tool은 호출되지 않아야 한다.

### drug_search_with_rag route

- `drug_search_tool`과 `rag_search_tool`이 모두 호출되어야 한다.
- Drug tool은 status를 반환해야 한다.
- RAG tool result와 final chunk가 일치해야 한다.
- 두 tool 모두 error가 없어야 한다.

### pharmacology intent

- route만으로 판단하지 않는다.
- 질문에 반감기, 대사, 배출, 얼마나 지나 같은 약리 정보 의도가 있으면 `pharmacology_info_tool`이 호출되어야 한다.
- Pharmacology tool은 status를 반환해야 한다.
- Pharmacology tool error가 없어야 한다.
- 반대로 약리 의도가 없는 질문에서는 pharmacology tool이 호출되지 않아야 한다.

## 로컬 검증 결과

LangSmith 업로드 없이 `DEFAULT_CASES` 10개에 대해 로컬 target/evaluator를 실행했다.

결과:

- avg_tool_contract: 1.0
- avg_retrieval_quality: 1.0

케이스별 결과:

| Case | Route | RAG Tool | Drug Tool | Pharmacology Tool | Tool Contract | Retrieval Quality |
|---|---|---|---|---|---:|---:|
| definition_s0 | rag | rag_search_tool | None | None | 1.0 | 1.0 |
| drug_tylenol | drug_search | None | drug_search_tool | None | 1.0 | 1.0 |
| drug_pseudoephedrine | drug_search_with_rag | rag_search_tool | drug_search_tool | None | 1.0 | 1.0 |
| procedure_tue | rag | rag_search_tool | None | None | 1.0 | 1.0 |
| field_dco_identity | rag | rag_search_tool | None | None | 1.0 | 1.0 |
| field_night_blood | rag | rag_search_tool | None | None | 1.0 | 1.0 |
| field_injury_delay | rag | rag_search_tool | None | None | 1.0 | 1.0 |
| drug_nasal_spray | drug_search_with_rag | rag_search_tool | drug_search_tool | None | 1.0 | 1.0 |
| field_leave_station | rag | rag_search_tool | None | None | 1.0 | 1.0 |
| drug_half_life | rag | rag_search_tool | None | pharmacology_info_tool | 1.0 | 1.0 |

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

이번 결과는 LangGraph retrieve node, drug search node, pharmacology node가 각각 tool을 거치도록 변경된 뒤에도 기존 retrieval 품질이 유지되며, route/intent별 tool 호출 계약이 지켜진다는 근거다.

이는 MCP 노출 전 중요한 기준선이다.
MCP로 tool을 노출하기 전에 tool input/output contract가 내부 graph에서 먼저 안정적으로 검증되어야 하기 때문이다.
