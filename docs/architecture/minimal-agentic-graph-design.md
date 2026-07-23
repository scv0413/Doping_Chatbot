# Minimal Agentic Graph Design

## Goal

2단계 agentic graph의 목표는 복잡한 agent를 만드는 것이 아니라, retrieval이 명백히 부족할 때만 1회 재시도하는 방어적 graph를 만드는 것이다.

현재 graph는 여전히 다음 원칙을 유지한다.

- answer 생성 전 무한 loop를 만들지 않는다.
- retrieval retry는 최대 1회만 허용한다.
- LangGraph state에는 데이터만 저장한다.
- 실행 의존성은 `ChatGraphDependencies`로 주입한다.
- 정상 검색 케이스에서는 기존 pipeline-equivalent 동작을 최대한 유지한다.

## Flow

```text
START
  -> route
  -> drug_search?
  -> rewrite
  -> retrieve
  -> retry_rewrite?
  -> retrieve?
  -> answer
  -> exit
  -> END
```

## Retry Condition

런타임 graph는 LangSmith evaluator처럼 reference answer를 알 수 없다. 따라서 실제 graph 안에서는 다음 관찰 가능한 신호만 사용한다.

- 검색 결과가 비어 있음: `empty_results`
- 검색 context가 지나치게 짧음: `low_context`
- best distance가 너무 약함: `weak_similarity`

현재 기준:

- `MAX_RETRIEVAL_ATTEMPTS = 2`
- `MIN_RETRIEVAL_CONTEXT_CHARS = 80`
- `MAX_ACCEPTABLE_BEST_DISTANCE = 0.85`

`MAX_RETRIEVAL_ATTEMPTS = 2`는 최초 검색 1회와 retry 검색 1회를 의미한다.

## Retry Query

재시도 query는 기존 rewritten query에 다음 보강어를 추가한다.

- 공식 근거
- 규정
- 절차
- 주의
- 금지목록
- KADA
- WADA

이 방식은 LLM을 호출하지 않고 deterministic하게 동작한다. 따라서 비용과 지연을 거의 늘리지 않으면서 검색 실패를 한 번 보정할 수 있다.

## Observability

`ChatPipelineResult`에 다음 필드를 추가했다.

- `retrieval_attempts`
- `retrieval_retry_reason`

LangSmith graph eval output에도 같은 값을 포함해 retry 발생 여부를 추적할 수 있게 했다.

## Detected Error and Fix

처음에는 `MIN_RETRIEVAL_CONTEXT_CHARS = 200`으로 설정했다. 그러나 한국어 근거 chunk나 테스트 fixture에서는 짧지만 충분한 답변 근거가 있을 수 있어 정상 결과도 `low_context`로 오판했다.

수정:

- threshold를 `80`으로 낮췄다.
- 테스트 fixture도 너무 짧은 검색 결과가 아니라 현실적인 길이의 근거 텍스트를 반환하도록 보정했다.

이 결정의 의미는 agentic retry를 공격적으로 돌리지 않고, 명백한 실패 상황에서만 작동하게 하는 것이다.

## Validation

```bash
uv run ruff check app tests
uv run pytest tests/chat/graph/test_chat_graph.py
uv run pytest
uv run python -m app.chat.evals.compare_retrieval_graph_eval --top-k 3 --rewrite
uv run python -m app.chat.evals.langsmith_graph_eval --top-k 3 --skip-dataset-upload
```

결과:

- ruff: pass
- graph tests: 7 passed
- full tests: 68 passed, 1 warning
- baseline retrieval_quality: 1.00
- graph retrieval_quality: 1.00
- LangSmith graph experiment: `graph-retrieval-top3-llm-False-1685a029`

## Presentation Point

발표에서는 이렇게 말하면 된다.

> LangGraph를 도입한 뒤 바로 복잡한 agent loop를 만들지 않았습니다. 먼저 기존 retrieval 품질이 유지되는 것을 확인했고, 그 다음 검색 실패에만 반응하는 최소 agentic retry를 추가했습니다. retry는 최대 1회로 제한했고, empty result, low context, weak similarity처럼 런타임에서 관찰 가능한 신호만 사용했습니다. 또한 retry 발생 여부를 `retrieval_attempts`와 `retrieval_retry_reason`으로 노출해 LangSmith에서 추적 가능하게 만들었습니다.
