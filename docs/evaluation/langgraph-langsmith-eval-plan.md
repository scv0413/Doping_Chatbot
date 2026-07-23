# LangGraph to LangSmith Eval Plan

## Current Position

현재 프로젝트는 다음 순서로 안정화되어 있다.

```text
preprocess -> chunks -> vector DB -> retriever -> router -> drug_search -> answer formatter/chain -> chat_pipeline -> LangGraph wrapper -> LangSmith graph eval
```

LangGraph는 아직 agent가 아니다. 1차 목적은 기존 `chat_pipeline`과 동일하게 동작하는 graph 실행 경로를 만들고, 그 실행을 LangSmith에서 추적/평가할 수 있게 연결하는 것이다.

## Why This Order Is Correct

LangGraph를 먼저 복잡한 agent로 만들면 오류 원인을 분리하기 어렵다.

따라서 현재 순서는 다음 이유로 적절하다.

- 기존 pipeline이 먼저 검증되어 있어 graph의 동작 보존 여부를 비교할 수 있다.
- retrieval-only eval 기준을 이미 갖고 있어 graph도 같은 기준으로 평가할 수 있다.
- graph state가 데이터 중심으로 설계되어 LangSmith trace와 checkpoint 확장에 유리하다.
- agentic loop, retry, tool selection은 이후 단계로 미뤄 infinite loop와 state bloat 위험을 줄였다.

## Added File

- `app/chat/evals/langsmith_graph_eval.py`
  - LangGraph 실행 결과를 LangSmith evaluation target으로 연결한다.
  - 기존 retrieval-only evaluator를 재사용한다.
  - `run_chat_graph`를 실행하지만 평가는 route/source/term/context 기준으로 한다.

- `tests/chat/evals/test_langsmith_graph_eval.py`
  - LangSmith에 실제 연결하지 않고 target output shape를 검증한다.

## Evaluation Strategy

이번 단계는 LLM answer quality 평가가 아니다.

평가 기준은 기존 retrieval-only 기준을 그대로 사용한다.

- route가 기대값과 같은가
- 기대 source가 검색 결과에 포함되는가
- must include term이 검색 context에 들어오는가
- context budget이 과도하지 않은가
- pipeline error가 없는가

## Validation Commands

```bash
uv run ruff check app tests
uv run pytest
uv run python -m app.chat.evals.langsmith_graph_eval --top-k 3 --skip-dataset-upload
```

## Validation Result

- ruff: pass
- pytest: 63 passed, 1 warning
- LangSmith graph eval: success
- Experiment: `graph-retrieval-top3-llm-False-d5e3b8ff`
- Cases processed: 10

## Detected Errors and Fixes

1. 문자열 생성 오류

문제:

`langsmith_graph_eval.py`와 test file 생성 과정에서 `\n`이 Python 문자열 내부 escape가 아니라 실제 줄바꿈으로 들어가 syntax error가 발생했다.

해결:

문자열을 명시적으로 `"\\n"` 또는 괄호로 이어붙이는 방식으로 수정했다.

2. unused import

문제:

`build_langsmith_examples`를 import했지만 사용하지 않아 ruff `F401`이 발생했다.

해결:

불필요한 import를 제거했다.

## Next Step

다음 단계는 LangSmith 화면에서 graph eval 결과를 확인하고, 기존 retrieval eval과 graph retrieval eval의 점수가 같은지 비교하는 것이다.

그 다음에야 agentic 확장으로 넘어간다. agentic 확장 후보는 다음과 같다.

- retrieval 결과 부족 시 query rewrite 재시도
- drug search 결과가 불명확할 때 clarification question 생성
- 공식 근거 부족 시 safe fallback answer
- report generation/tool call 분기


## Nasal Spray Case Revision

`drug_nasal_spray` 케이스는 WADA 금지목록의 특정 예외를 직접 검색하는 문제로 두지 않는다. 비강 스프레이라도 제품과 성분에 따라 판단이 달라지므로, 답변과 검색은 제품명/성분명/KADA 약물검색으로 유도하는 방향을 우선한다.

이 결정에 따라 expected source는 `field_response_manual`로 조정했고, must include term도 `제품명`, `성분` 중심으로 바꿨다.

재검증 결과 LangSmith graph eval experiment `graph-retrieval-top3-llm-False-5700bd6e`가 성공적으로 실행되었다.
