# Structure Audit Before Agentic Expansion

## Current Stage

현재 프로젝트는 LangGraph 1차 wrapper와 LangSmith retrieval-only graph eval까지 연결된 상태다.

아직 agentic loop, tool retry, report generation, FastAPI/Gradio UI는 붙이지 않았다. 따라서 지금 단계의 핵심 검증 기준은 다음이다.

- 기존 preprocessing/retrieval/chat pipeline 구조가 깨지지 않았는가
- LangGraph가 기존 pipeline과 동일한 결과를 낼 수 있는가
- LangSmith eval에서 graph 실행을 추적할 수 있는가
- 코드 문법과 테스트가 안정적인가

## Directory Structure

```text
app/
  preprocess/
    PDF/manual source를 page/chunk 단위로 정제하는 영역

  chat/
    answer/
      formatter와 LLM answer chain

    drug_search/
      KADA 약물검색 adapter, mock searcher, drug search result formatter

    retrieval/
      query rewrite, Chroma indexer/retriever, vector store wrapper

    router/
      사용자 질문을 rag, drug_search, drug_search_with_rag로 분류

    pipeline/
      router + drug_search + retrieval + answer를 순차 실행하는 기존 기준 pipeline

    graph/
      기존 pipeline 동작을 LangGraph node 구조로 감싼 1차 graph

    policy/
      RAG 6 rules, safety caveat, persona/tone, citation policy

    evals/
      로컬 retrieval 실험, LangSmith retrieval/answer/graph eval runner

    docs/
      설계 판단, 발표용 설명, source/eval/graph 문서

tests/
  chat/
    answer/
    drug_search/
    evals/
    graph/
    pipeline/
    policy/
    router/
```

## Role Separation

### preprocess

문서 원문을 다룬다. PDF layout 문제, manual source, chunk id, metadata 생성은 이 영역의 책임이다.

### chat/retrieval

이미 생성된 chunk를 검색 가능한 형태로 만든다. Chroma index 생성, embedding, 검색, query rewrite가 여기에 있다.

### chat/drug_search

약물명/제품명/성분명 조회처럼 문서 RAG만으로 해결하기 어려운 tool 성격의 기능이다.

### chat/pipeline

현재까지의 기준 실행 경로다. LangGraph 도입 전후 결과 비교의 기준점이다.

### chat/graph

LangGraph 1차 구현이다. agent가 아니라 기존 pipeline을 node로 나눈 orchestration layer다.

### chat/evals

성능과 품질을 숫자로 확인하는 영역이다.

- retrieval eval: 검색 품질
- answer eval: formatter/LLM 답변 품질
- graph eval: LangGraph 실행이 retrieval 기준을 유지하는지 확인

## Syntax and Test Validation

실행한 검증:

```bash
uv run ruff check app tests
uv run pytest
uv run python -m compileall -q app tests
```

결과:

- ruff: pass
- pytest: 63 passed, 1 warning
- compileall: pass

경고:

- LangSmith dependency 내부의 `ast.Str` deprecation warning
- 현재 프로젝트 코드 오류는 아님

## Structure Validation

현재 구조는 다음 확장에 적합하다.

- LangSmith graph tracing
- retrieval-only eval과 answer eval 비교
- agentic retry node 추가
- report generation tool 추가
- FastAPI 또는 Gradio wrapper 추가

다만 agentic 확장 전에 유지해야 할 원칙이 있다.

1. `chat_pipeline`은 당분간 기준 implementation으로 남긴다.
2. `graph`는 pipeline과 동등성을 유지한 상태에서만 확장한다.
3. LangGraph state에는 데이터만 넣고, 실행 함수/LLM client는 dependency로 주입한다.
4. retrieval eval과 graph eval은 같은 case/evaluator를 공유한다.
5. 약물 질문은 route/form만으로 단정하지 않고 제품명/성분명 기반 search로 유도한다.

## Detected Cleanup Points

- `__pycache__`와 `.DS_Store`는 파일 시스템에는 존재하지만 `.gitignore`에 포함되어 있어 commit 대상은 아니다.
- `data/processed`, `data/indexes`, `logs`도 `.gitignore`에 포함되어 있다.
- 현재 git status에는 새로 추가된 graph/evals/policy/docs 파일들이 untracked로 남아 있으므로 commit 전 `git add` 범위를 의도적으로 선택해야 한다.

## Next Plan

다음 단계는 세 갈래 중 하나를 선택하면 된다.

1. LangSmith 결과 비교 정리
   - 기존 retrieval eval과 graph retrieval eval을 비교해 “Graph 도입 후 품질 유지”를 포트폴리오 근거로 남긴다.

2. Graph에 최소 agentic 분기 추가
   - retrieval result가 부족할 때만 rewrite/retrieve를 1회 재시도한다.
   - recursion limit과 exit node를 유지한다.

3. UI/API 전 단계 adapter 정리
   - Gradio/FastAPI에서 호출할 `run_chat` entrypoint를 고정한다.
   - 나중에 UI를 붙여도 pipeline/graph 내부 구조를 몰라도 되게 한다.

추천은 1번 후 2번이다. 먼저 LangSmith 비교 근거를 완성하고, 그 다음 agentic retry를 작게 붙이는 순서가 가장 안전하다.
