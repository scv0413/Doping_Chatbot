# Answer Evaluation Plan

## 목적

Retrieval-only 평가 이후, 실제 사용자가 보게 되는 최종 답변의 기본 구조를 검증한다.
첫 단계에서는 LLM을 끄고 `use_llm=false` deterministic formatter 출력만 평가한다.

## 왜 formatter부터 평가하는가

LLM을 켜면 문장 표현이 매번 달라질 수 있다. 따라서 먼저 같은 입력에 같은 출력을 내는 formatter를 평가해 다음을 확인한다.

- 답변 섹션이 유지되는가
- 필수 안전 문구가 있는가
- 근거 섹션과 chunk id가 유지되는가
- 약물/현장 대응 질문에서 필요한 확인 항목이 누락되지 않는가

## 1차 케이스

- `definition_s0`
- `drug_pseudoephedrine`
- `procedure_tue`
- `field_dco_identity`
- `field_night_blood`

## Evaluator

- `answer_route_match`: route가 기대값과 일치하는지
- `answer_must_include`: 필수 개념 그룹이 답변에 포함되는지
- `answer_must_not_include`: 위험한 단정 표현이 없는지
- `answer_citation_presence`: 근거 섹션과 chunk id가 유지되는지
- `answer_safety_disclaimer`: 공식 판정을 대체하지 않는다는 문구가 있는지
- `answer_pipeline_errors`: pipeline error가 없는지

## 실행

```bash
uv run python -m app.chat.evals.langsmith_answer_eval --top-k 3
```

LLM 답변 평가는 formatter 기준이 안정화된 뒤 다음 단계에서 실행한다.


## 2차: LLM Answer Chain 평가

formatter 기준이 안정화된 뒤 같은 5개 케이스로 `use_llm=true` 평가를 실행한다.
이 단계의 목적은 LLM이 구조화 답변을 자연스럽게 다듬는 과정에서 다음을 빠뜨리지 않는지 확인하는 것이다.

- 필수 개념
- 위험 단정 금지
- 근거 섹션과 chunk id
- 공식 판정 대체 불가 문구
- pipeline error 없음

실행:

```bash
uv run python -m app.chat.evals.langsmith_answer_eval --top-k 3 --use-llm
```
