# Policy Layer Design

## 목적

LangGraph로 넘어가기 전에 RAG 답변 품질을 통제하는 6가지 rule을 중앙화한다.
이 policy는 prompt에만 쓰는 문구가 아니라 formatter, evaluator, 이후 LangGraph safety node가 함께 참조할 source of truth다.

## 위치

```text
app/chat/policy/
  __init__.py
  answer_policy.py
```

## RAG Answer 6 Rules

| rule_id | name | 실무 의미 | 도핑 챗봇 적용 |
|---|---|---|---|
| `restrict_to_context` | Restrict to Context | 제공된 retrieved chunks와 tool output 안에서만 답변 | KADA 약물검색 결과, RAG 문서 근거, manual source 안에서만 답변 |
| `explicit_citations` | Explicit Citations | 사실 주장에 추적 가능한 출처를 유지 | 문서명, page, chunk_id를 근거 섹션에 유지 |
| `handle_insufficient_info` | Handle Insufficient Info | 문맥에 답이 없으면 추측하지 않고 모른다고 말함 | 검색된 근거만으로 확인 불가 시 KADA/팀 닥터/약사 확인 안내 |
| `prevent_fabrication` | Prevent Fabrication | 자료, 수치, 출처, 결론을 지어내지 않음 | 복용 가능 여부, 혈액검사 대체 가능 여부, 반감기 등을 근거 없이 단정하지 않음 |
| `enforce_persona_tone` | Enforce Persona/Tone | 대상 사용자와 어휘 수준을 일관되게 유지 | 엘리트 선수와 트레이너가 바로 이해할 수 있는 짧고 명확한 한국어 |
| `apply_safety_caveats` | Apply Safety Caveats | 경고, 면책, 조건부 표현을 포함 | 공식 판정 대체 불가, 복용 전 확인, 현장에서는 확인/기록/동석 요청 우선 |

## 포함 내용

- `AnswerRule`
- `CHATBOT_PERSONA`
- `ANSWER_RULES`
- `ANSWER_RULES_BY_ID`
- `OFFICIAL_DECISION_DISCLAIMER`
- `INSUFFICIENT_CONTEXT_MESSAGE`
- `DRUG_USE_SAFETY_NOTE`
- `FIELD_RESPONSE_SAFETY_NOTE`
- prompt builder helper

## 연결 지점

- `app/chat/answer/chain.py`
  - system prompt와 작성 지침을 policy에서 생성
  - LLM은 RAG 6 rules를 명시적으로 받음
- `app/chat/answer/formatter.py`
  - 공식 판정 대체 불가 문구, 약물/현장 공통 주의문을 policy에서 참조
- `app/chat/evals/langsmith_answer_eval.py`
  - citation evaluator와 safety evaluator가 policy rule id와 연결됨
- `tests/chat/policy/test_answer_policy.py`
  - 6 rule의 id, 설명, 도핑 적용 방식이 유지되는지 검증

## 설계 판단

기존 도핑 도메인 원칙은 버리지 않고 RAG 6 rule의 `doping_application`으로 흡수했다.
예를 들어 “현장에서는 충돌보다 확인/기록/동석 요청”은 독립 rule이 아니라 `apply_safety_caveats`의 도핑 적용이다.

case-specific 행동 지침은 아직 formatter에 남겼다.
이유는 S0, 슈도에페드린, TUE, 검사관 신분, 새벽 혈액 시료 같은 도메인별 답변은 공통 policy보다 답변 템플릿에 가깝기 때문이다.

## 검증

- `uv run ruff check app tests`
- `uv run pytest`
- LangSmith formatter answer eval
- LangSmith answer chain eval
