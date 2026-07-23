# Field Scenario LangSmith Eval

## 목적

Runtime Policy는 반감기 질문에는 formatter를, 복합 현장 상황에는 LLM answer chain을 사용하도록 설계했다. 이 정책을 설득력 있게 만들려면 “복합 현장 상황에서 LLM이 필요한가?”를 별도 평가셋으로 비교해야 한다.

이번 단계에서는 field scenario 전용 평가셋과 evaluator를 만들고, 우선 `use_llm=False` formatter 기준선을 로컬에서 검증했다.

## 평가 케이스

`app/chat/evals/field_scenario_cases.py`에 5개 케이스를 정의했다.

- 검사관 또는 시료채취요원 신분 불명확
- 새벽 또는 야간 혈액 시료 채취 요청
- 부상 치료가 먼저 필요한 상황에서 검사 지연 요청
- 도핑검사 중 짐을 가지러 현장을 벗어나야 하는 상황
- TUE 신청 방법과 대리 신청 가능 여부

## 평가 기준

`app/chat/evals/langsmith_field_scenario_eval.py`는 다음 evaluator를 제공한다.

- `field_route_match`: 현장 질문이 RAG로 라우팅되는지 확인
- `field_required_info`: 신분 확인, 통역/동석, 기록, 공식 절차, 위험 행동 회피 같은 필수 개념 포함 여부
- `field_unsafe_action_absent`: 그냥 거부, 현장 이탈, 무조건 대체 같은 위험한 행동 지시가 없는지 확인
- `field_action_order`: 먼저 확인하고, 도움을 요청하고, 기록하는 순서가 유지되는지 확인
- `field_safety_posture`: 정중한 협조, 기록, 동석, 공식 확인 같은 현장 안전 태도 확인
- `field_citation_presence`: 근거 섹션과 chunk id가 있는지 확인
- `field_safety_disclaimer`: 공식 판정 대체 불가 문구가 있는지 확인
- `field_pipeline_errors`: pipeline 오류가 없는지 확인

## 발견한 문제와 수정

처음 formatter 기준선은 평균 0.9592였다. 두 가지 문제가 드러났다.

첫째, “도핑검사 중 짐을 가지러 현장을 벗어나도 되나?”라는 질문에서 `field_response_manual:s3`가 top1으로 검색됐는데도 행동 지침은 새벽 혈액 시료채취 쪽 내용으로 섞여 나왔다. 원인은 `formatter.py`의 branch 순서였다. `s1`, `s2` branch가 먼저 잡히고 `s3` 전용 branch가 없어서 현장 이탈/부상 지연 상황이 제대로 표현되지 않았다.

수정:

- `field_response_manual:s3` 전용 branch 추가
- 짐/현장 이탈 질문에는 “검사관에게 알림 → 허가 요청 → 동행 또는 동석 → 기록” 순서로 안내
- 부상/치료 질문에는 “거부라고 표현하지 않음 → 치료 필요성 설명 → 의료진/동석 요청 → 기록” 순서로 안내
- `s3` branch를 `s1`, `s2`보다 먼저 평가하도록 순서 조정

둘째, TUE 답변에서 “무조건 승인되거나 승인을 보장하는 절차가 아니다”라는 안전 문구가 `무조건 승인` 금지어로 오탐됐다.

수정:

- `unsafe_action_evaluator`에 부정 표현 감지 로직 추가
- `아닙니다`, `않습니다`, `아니므로`, `보장하는 절차가 아니` 같은 표현이 가까이 있으면 위험 지시로 보지 않도록 수정

## 로컬 평가 결과

formatter 기준 로컬 평가 결과:

- top_k: 3
- use_llm: false
- average score: 0.995

케이스별로 대부분 1.0을 달성했다. TUE 케이스의 `field_safety_posture`만 0.8인데, 이 항목은 원래 현장 충돌 상황에 더 적합한 평가축이라 TUE 절차형 질문에는 약간 엄격하게 작동한다.

## LangSmith 실행 상태

LangSmith 업로드/실행은 현재 차단됐다.

차단 사유:

- field scenario eval은 로컬 문서에서 검색된 근거와 생성 답변을 LangSmith 외부 서비스로 업로드한다.
- `use_llm=True` 비교는 검색된 로컬 문서 컨텍스트를 OpenAI로 보낼 수 있다.

따라서 현재 완료된 것은 다음까지다.

- 평가셋 생성
- evaluator 생성
- formatter 기준 로컬 평가
- formatter 버그 수정
- 전체 테스트와 lint 통과

LangSmith formatter/LLM 비교 실행은 사용자가 외부 업로드와 LLM 전송을 명시 승인하면 진행한다.

## 검증 결과

- `uv run pytest tests/chat/answer/test_answer_formatter.py tests/chat/evals/test_langsmith_field_scenario_eval.py`
  - 9 passed

- `uv run pytest`
  - 119 passed, 1 warning

- `uv run ruff check app tests`
  - All checks passed

## 발표 관점 설명

이 단계의 핵심은 Runtime Policy를 감으로 정하지 않았다는 점이다.

반감기 eval에서는 formatter와 LLM이 모두 안전 기준을 통과했지만, 운영 기본값은 비용과 안정성을 고려해 formatter로 결정했다. 이번 field scenario eval은 반대로 복합 현장 상황에서 LLM이 왜 필요한지 확인하기 위한 평가 기반을 만든 것이다.

중요한 발견은 LLM 이전에 formatter 기준선 자체도 좋아야 한다는 점이었다. 평가를 돌려보니 현장 이탈 질문에서 혈액검사 행동 지침이 섞이는 문제가 발견됐고, 이를 formatter branch 개선으로 수정했다. 즉 evaluation이 단순 점수 측정이 아니라 실제 버그를 찾아내는 도구로 작동했다.
