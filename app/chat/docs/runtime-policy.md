# Runtime Policy

## 목적

Runtime Policy는 Gradio와 FastAPI가 `top_k`, `use_llm`, `engine` 같은 내부 실행 옵션을 직접 판단하지 않도록 만드는 운영 계층이다.

사용자는 질문만 입력하고, 시스템은 질문 성격에 따라 다음을 자동 결정한다.

- 검색 문서 수: `top_k`
- 답변 생성 방식: deterministic formatter 또는 LLM answer chain
- 실행 엔진: LangGraph 또는 pipeline
- graph recursion limit

## 왜 필요한가

LangSmith 비교 결과에서 half-life/pharmacology 케이스는 `use_llm=False`와 `use_llm=True` 모두 안전 기준을 통과했다.

하지만 운영 관점에서는 두 방식의 의미가 다르다.

- formatter는 빠르고 비용이 낮으며 안전 문구가 안정적이다.
- LLM answer chain은 자연어 설명력이 좋지만 지연시간과 비용이 늘고, 위험 도메인에서는 단정 표현을 계속 감시해야 한다.

따라서 사용자가 직접 옵션을 고르게 두기보다, 서비스가 목적에 맞는 기본 정책을 선택하도록 만들었다.

## 현재 정책

- 특정 약물 + 반감기 질문
  - 예: `슈도에페드린 반감기가 얼마나 돼?`
  - `use_llm=False`
  - 이유: 반감기는 안전 문구와 필수 확인 정보가 중요한 영역이라 deterministic formatter를 기준선으로 둔다.

- 단순 약물 조회
  - 예: `타이레놀 먹어도 돼?`
  - `use_llm=False`
  - 이유: KADA 약물검색 결과를 왜곡하지 않고 구조화해서 보여주는 것이 우선이다.

- 복합 현장 상황
  - 예: 검사관 신분 불명확, 새벽 혈액 시료채취, 부상 치료, TUE 신청 방법
  - `use_llm=True`
  - 이유: 여러 조건을 순서 있게 설명하고 사용자가 해야 할 행동을 자연스럽게 정리하는 것이 중요하다.

- 기본 실행 엔진
  - `graph`
  - 이유: LangGraph guardrail, retry, 추적 구조로 확장하기 좋다.

- 기본 검색 문서 수
  - `top_k=3`
  - 이유: 기존 retrieval/graph/half-life eval에서 품질과 비용 균형이 가장 좋게 나온 기준이다.

## 구현 파일

- `app/chat/policy/runtime_policy.py`
  - `decide_runtime_policy`
  - `RuntimePolicyDecision`
  - `RuntimeEngine`

- `app/chat/runtime.py`
  - `ChatRequest`에서 `top_k`, `use_llm`, `engine`, `recursion_limit`을 선택값으로 변경
  - 요청에 값이 없으면 Runtime Policy로 채움
  - 명시적 값이 있으면 실험과 테스트를 위해 override로 존중

- `app/chat/ui/gradio_app.py`
  - 사용자 화면에서 `검색 문서 수`, `LLM 답변 사용`, `실행 엔진` 옵션 제거
  - 내부적으로 `run_chat(ChatRequest(query=...))`만 호출

## LangSmith 비교 판단

Half-life formatter 실험:

- `half-life-formatter-top3-b93a1015`
- deterministic formatter 기준
- local score: 1.0

Half-life LLM answer chain 실험:

- `half-life-answer-chain-top3-830eacfe`
- LLM answer chain 기준
- local score: 1.0

결론:

- 품질 기준은 둘 다 통과했다.
- 운영 기본값은 비용과 안전성을 고려해 반감기 질문에서 formatter를 선택한다.
- LLM은 복합 현장 상황 설명에 우선 사용한다.

## 검증 결과

- Runtime Policy 단위 테스트: 통과
- Runtime/API/UI 관련 테스트: 통과
- 전체 테스트: `113 passed, 1 warning`
- 전체 lint: `All checks passed`
- fake dependency smoke test:
  - 반감기 질문: `use_llm=False`, `graph`, `top_k=3`
  - 복합 현장 질문: `use_llm=True`, `graph`, `top_k=3`

## 발표 관점 설명

이 구조의 핵심은 “LLM을 쓸 수 있다”가 아니라 “언제 LLM을 쓰고 언제 안 쓸지 운영 기준을 세웠다”는 점이다.

포트폴리오에서 강조할 말은 다음과 같다.

> LangSmith 평가로 formatter와 LLM answer chain의 품질을 비교했고, 반감기처럼 안전 문구가 중요한 질문은 빠르고 안정적인 formatter를 기본값으로 정했습니다. 반면 검사관 신분, 새벽 혈액 시료채취, 부상 치료처럼 맥락 설명이 중요한 질문은 LLM answer chain을 사용하도록 Runtime Policy를 만들었습니다. UI와 API는 내부 옵션을 몰라도 되고, 운영 정책은 한 곳에서 관리됩니다.
