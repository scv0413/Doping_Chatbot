# LangSmith Retrieval-Only Evaluation Plan

## 목적

LangSmith는 LLM 답변 평가를 바로 시작하기 위한 도구가 아니라, 먼저 검색 품질을 반복 추적하기 위한 실험 기록 시스템으로 사용한다.
이번 단계에서는 answer chain을 호출하지 않고 retrieval 결과만 평가한다.

## 실행 범위

- LangSmith Dataset: 대표 질문 10개
- Target: router -> optional query rewrite -> retriever
- Evaluator: route match, source hit, term hit, context budget, retrieval quality
- LLM answer evaluation: 제외

## 파일 역할

- `app/chat/evals/cases.py`
  - 로컬 runner와 LangSmith runner가 공유하는 대표 질문과 기대 기준
- `app/chat/evals/retrieval_token_experiment.py`
  - 로컬 실험과 빠른 회귀 확인
- `app/chat/evals/langsmith_retrieval_eval.py`
  - LangSmith dataset 업로드와 retrieval-only evaluation 실행

## 추천 실행

```bash
uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 3 --rewrite
```

비교 실험은 다음처럼 개별 experiment로 실행한다.

```bash
uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 3 --no-rewrite
uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 3 --rewrite
uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 5 --no-rewrite
uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 5 --rewrite
```

## 다음 단계

retrieval-only 결과가 안정되면 answer formatter/chain을 포함한 answer evaluation으로 확장한다.
그 뒤 LangGraph를 붙였을 때 node별 trace를 확인한다.
