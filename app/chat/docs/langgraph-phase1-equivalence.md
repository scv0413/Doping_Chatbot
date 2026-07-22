# LangGraph Phase 1: Pipeline Equivalence

## Goal

1차 LangGraph의 목표는 새로운 기능 추가가 아니라 기존 `run_chat_pipeline`과 동일하게 동작하는 graph wrapper를 만드는 것이다.

즉, 현재 단계에서 LangGraph는 agent가 아니라 orchestration layer다. 기존 pipeline에서 이미 검증한 router, drug search, retrieval, answer formatter/chain의 순서를 LangGraph 노드로 분리해 이후 분기, 재시도, LangSmith trace, agentic tool 호출을 붙일 수 있는 구조를 만든다.

## Node Flow

```text
START
  -> route
  -> drug_search?
  -> rewrite?
  -> retrieve?
  -> answer
  -> exit
  -> END
```

- `route`: 사용자 질문을 `rag`, `drug_search`, `drug_search_with_rag` 중 하나로 분류한다.
- `drug_search`: 약물성 질문이면 KADA 약물 검색 또는 mock searcher를 호출한다.
- `rewrite`: retrieval 질문을 확장한다. 현재는 query rewriter와 동일한 역할이다.
- `retrieve`: Chroma vector DB에서 근거 chunk를 검색한다.
- `answer`: 기존 answer chain 또는 deterministic formatter로 답변을 만든다.
- `exit`: 답변 누락 같은 비정상 종료를 마지막으로 방어한다.

## Design Decision

초기 초안에서는 `router`, `retriever`, `llm` 같은 실행 의존성을 graph state에 넣을 수 있었다. 하지만 1차 구현에서 바로 수정했다.

이유는 LangGraph의 state는 가능한 한 “업무 데이터와 중간 결과”만 담아야 하기 때문이다. 실행 함수나 LLM 클라이언트를 state에 넣으면 state bloat가 생기고, 추후 LangSmith trace, checkpoint, replay, persistence에서 보기 어려운 구조가 된다.

따라서 현재 구조는 다음처럼 나눈다.

- `ChatGraphState`: query, decision, drug_result, retrieval_matches, answer, errors 같은 데이터만 저장한다.
- `ChatGraphDependencies`: router, drug_searcher, retriever, query_rewriter, llm 같은 실행 의존성을 graph compile 시점에 주입한다.

## Guardrails

- `recursion_limit=12`을 기본값으로 둬 infinite loop를 방지한다.
- 1차 graph는 loop가 없는 DAG 구조로 만든다.
- `exit` node를 둬 graph가 답변 없이 끝나는 경우를 방어한다.
- 아직 message trimming이나 summarization node는 넣지 않는다. 현재 graph는 multi-turn message state가 아니라 single query pipeline이기 때문이다.

## Validation

검증 기준은 “기존 pipeline과 graph 결과가 같은가”다.

실행한 검증:

```bash
uv run ruff check app tests
uv run pytest tests/chat/graph/test_chat_graph.py
uv run pytest
uv run python -m app.chat.graph.graph_inspector '도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?' --no-llm
```

결과:

- ruff: pass
- graph tests: 5 passed
- full tests: 62 passed, 1 LangSmith dependency warning
- graph inspector: `route=rag`, `errors=0`, top chunks retrieved successfully

## Presentation Point

발표에서는 이렇게 말하면 된다.

> LangGraph를 바로 agent로 쓰지 않고, 먼저 기존 pipeline과 동일한 동작을 하는 graph로 감쌌습니다. 이유는 orchestration layer를 바꿀 때 가장 중요한 것이 기능 추가가 아니라 동작 보존이기 때문입니다. 그래서 route, drug search, query rewrite, retrieval, answer를 각각 node로 분리하고, pipeline 결과와 graph 결과가 같은지 테스트했습니다. 또한 state에는 실행 함수나 LLM 클라이언트를 넣지 않고 데이터만 남겨 future LangSmith tracing과 checkpoint 확장에 안전하게 만들었습니다.
