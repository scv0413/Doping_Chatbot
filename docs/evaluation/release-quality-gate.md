# Release Quality Gate

## Goal

LangSmith experiments are excellent for comparison and trace inspection, but a release candidate also needs a local command that clearly passes or fails. `scripts/release_quality_gate.py` runs the same deterministic graph tool target and evaluator logic against the current local index.

```bash
uv run python scripts/release_quality_gate.py
```

The command exits with code `1` when a required metric drops below its threshold, so it can be used in a staging job or a manually approved release workflow.

## Evaluated Contract

The gate uses the 10 core retrieval/tool cases and evaluates:

- `route_match`: intended route is selected;
- `source_hit`: at least one expected source is retrieved;
- `term_hit`: expected regulatory concepts appear in retrieved context;
- `retrieval_quality`: combined retrieval quality score;
- `tool_contract`: graph route and MCP-compatible tool output agree.

`route_match` and `tool_contract` must be exactly `1.0`. Source, term, and retrieval quality averages must be at least `0.9`.

## Result Interpretation

A passing gate proves the current indexed corpus and deterministic graph still satisfy this bounded regression suite. It does not prove all future athlete questions are correct, and it does not replace the LLM answer, field-scenario, or half-life LangSmith evaluations.

## Relationship with LangSmith

Run the gate before a release candidate, then run the focused LangSmith evaluations when the relevant surface changes:

```bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3
uv run python -m app.chat.evals.langsmith_field_scenario_eval --top-k 3
uv run python -m app.chat.evals.langsmith_half_life_eval --top-k 3
```

The release gate gives an executable local decision. LangSmith preserves experiment traces, latency, token/cost data, and comparison history.

## Reviewed Korean Manual Citation Gate

The LangSmith answer evaluator records `official_source_citations` from
retrieval metadata. When any retrieved source ID ends in `_human_reviewed`, the
`answer_reviewed_manual_official_citation` score requires an official source ID
and page in both the structured trace and the rendered answer. The evaluator is
not applicable until an approved human-reviewed source is indexed.

## ISTI 2023 Notification Rights Verification (2026-07-23)

WADA ISTI 2023 영문 원문 p.43-45를 기준으로 프로젝트 검수 한국어 안내문에 제5.4.1-5.4.5를 추가했다. 이 안내문은 공식 WADA 한국어 번역본이 아니며, 검색 결과와 답변은 항상 `wada_isti_2023_en`의 원문 쪽수를 함께 표시한다.

- indexed chunks: `580` (base, field manual, approved ISTI Korean guidance 포함)
- local release gate: 15 cases, `route_match=1.0`, `source_hit=1.0`, `term_hit=1.0`, `retrieval_quality=1.0`, `tool_contract=1.0`
- graph assertion: `통지서 서명을 거부하면 어떻게 돼?`는 `wada_isti_2023_ko_human_reviewed:5.4.3:c0`을 검색하고, 답변에 `wada_isti_2023_en`, p.44를 표시했다.
- full regression: `228 passed`; `ruff check app tests scripts` passed.
- LangSmith retrieval experiment: [retrieval-top3-rewrite-True-c25d84a7](https://smith.langchain.com/o/2d4720fb-5dfa-4666-983e-680c70b9ab87/datasets/aabceefb-4dbf-412c-9252-753697fdfb61/compare?selectedSessions=9eec1299-4641-4f67-88ca-227aee233144)
- LangSmith deterministic answer experiment: [answer-formatter-top3-b76d2603](https://smith.langchain.com/o/2d4720fb-5dfa-4666-983e-680c70b9ab87/datasets/a7f204a4-bd4e-410c-90ac-61b2a4453de0/compare?selectedSessions=632f4b89-daff-465d-91e6-eba3fef27b0a)
