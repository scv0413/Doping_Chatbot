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
