# Controlled Agent Plan in LangGraph

## What Changed

The graph now has a `plan` node immediately after router classification. It records an `AgentToolPlan` before any tool runs.

```text
route -> plan -> drug_search? -> pharmacology? -> rewrite -> retrieve -> answer -> exit
```

The plan is deterministic:

| Intent shape | Planned tool order |
| --- | --- |
| field/regulation question | `rag_search_tool` |
| simple product/ingredient question | `drug_search_tool` |
| drug plus regulation question | `drug_search_tool -> rag_search_tool` |
| substance half-life question | `drug_search_tool -> pharmacology_info_tool -> rag_search_tool` |

This is deliberately not a free-form LLM agent. The router and policy decide the bounded tool order, every tool keeps its Pydantic/MCP-compatible contract, and retrieval may retry only once when its observable quality signal is weak.

## Why It Matters

The plan separates intent from execution. A LangGraph/LangSmith trace can now show both what the system planned to call and what it actually called. `planned_tool_names` is included in the internal graph/runtime result and LangSmith graph tool target, while the public API response remains limited to user-facing answer fields.

## Guardrails

- No arbitrary LLM-selected tool names.
- No unbounded loop: retrieval retry remains limited to one additional attempt.
- `recursion_limit=12` covers the longest valid route after adding the plan node, including one retry; it is still a hard stop against accidental cycles.
- External MCP HTTP execution remains optional. The internal registry executor is the production default and is the fallback for MCP transport failure.

## Verification

The graph test suite verifies planned tool order for a pseudoephedrine half-life question. The complete suite then verifies that public API fields remain hidden and that the release quality gate preserves route/source/tool contract quality.
