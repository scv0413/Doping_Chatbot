# ISTI 2023 Notification Rights and Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the project-reviewed Korean ISTI 2023 guidance for athlete rights, identity verification, signature, and supervised delay, then protect it with retrieval and answer evaluations.

**Architecture:** The WADA ISTI 2023 English PDF remains the authority. Each Korean manual section carries the exact English page; the existing approved-manual loader creates indexable chunks. Existing LangSmith retrieval and deterministic answer datasets gain the field cases.

**Tech Stack:** Python 3.12, Pydantic, Chroma, LangGraph, LangSmith, pytest, Ruff.

## Global Constraints

- Korean project guidance is not an official WADA translation; every approved chunk retains `official_source_id = wada_isti_2023_en` and its source page.
- No OCR or machine-generated Korean text is indexed without `review_status = "approved"`.
- Do not imply that delay or temporary departure is freely allowed: DCO/Chaperone permission and continuous observation are conditions.
- Preserve `top_k=3` as the evaluation baseline.

---

### Task 1: Extend the reviewed ISTI 2023 notification guidance

**Files:**
- Modify: `docs/architecture/wada-isti-2023-korean-reviewed.md`
- Test: `tests/preprocess/test_approved_isti_2023_manual.py`

**Interfaces:**
- Consumes: `load_approved_manual_chunks(manual_path: Path) -> list[ManualChunkRecord]`
- Produces: Korean chunks for `5.4.1` through `5.4.5`, traced to official pages 43-45.

- [ ] Write a failing test asserting sections `5.4.1`, `5.4.2`, `5.4.3`, `5.4.4`, and `5.4.5` exist; assert `5.4.2` maps to p.44, `5.4.5` to p.45, and the delay section includes `지속 관찰`.
- [ ] Run `uv run python -m pytest tests/preprocess/test_approved_isti_2023_manual.py -q`; expect failure before new sections are added.
- [ ] Replace the p.42-only `5.4.1` note with reviewed p.43 rights/responsibilities guidance. Add `5.4.2`, `5.4.3`, `5.4.4`, and `5.4.5` from p.44-45, each with one `<!-- english-source-page: PAGE -->` marker.
- [ ] Run `uv run python scripts/build_approved_manual.py --manual-path docs/architecture/wada-isti-2023-korean-reviewed.md`; expect eight approved chunks.
- [ ] Commit with `docs: expand reviewed ISTI notification guidance`.

### Task 2: Add high-risk field retrieval and answer cases

**Files:**
- Modify: `app/chat/evals/cases.py`
- Modify: `app/chat/evals/answer_cases.py`
- Modify: `tests/chat/evals/test_langsmith_answer_eval.py`

**Interfaces:**
- Consumes: `EvalCase` and `AnswerEvalCase`.
- Produces: cases for DCO identity documentation, notification signature/refusal, and continuously observed delay.

- [ ] Write a failing test asserting retrieval cases `isti_identity_documentation`, `isti_notification_signature`, and `isti_station_delay_observation` are registered.
- [ ] Run `uv run python -m pytest tests/chat/evals/test_langsmith_answer_eval.py -q`; expect failure before registration.
- [ ] Add retrieval cases requiring `wada_isti_2023_ko_human_reviewed` or `wada_isti_2023_en`, and terms `신분증`, `서명`, `지속 관찰`, `정당한 사유`.
- [ ] Add answer safety cases that reject advice equivalent to `서명하지 말고 떠나` or `자유롭게 현장을 벗어나`.
- [ ] Run `uv run python -m pytest tests/chat/evals -q` and commit with `test: expand ISTI field scenario evaluations`.

### Task 3: Reindex and verify end-to-end quality

**Files:**
- Generated (ignored): `data/processed/approved_manual_chunks.jsonl`, `data/indexes/chroma/`
- Modify: `docs/evaluation/release-quality-gate.md`

**Interfaces:**
- Consumes: `get_default_chunk_paths()` and the approved manual JSONL.
- Produces: an indexed collection and LangSmith experiments that retain official-source citations.

- [ ] Run `uv run python scripts/build_approved_manual.py --manual-path docs/architecture/wada-isti-2023-korean-reviewed.md` and `uv run python -m app.chat.domain.retrieval.indexer`.
- [ ] Run deterministic graph query `통지서 서명을 거부하면 어떻게 돼?`; assert the approved Korean source is returned and the answer cites `wada_isti_2023_en`, p.44.
- [ ] Run `uv run python -m pytest -q`, `uv run ruff check app tests scripts`, `uv run python -m app.chat.evals.langsmith_retrieval_eval --top-k 3`, and `uv run python -m app.chat.evals.langsmith_answer_eval --top-k 3`.
- [ ] Record the exact pass results and citation invariant in the release quality document; commit with `docs: record ISTI notification quality gate`.

## Self-Review

- Task 1 covers the reviewed Korean source; Task 2 covers the high-risk field cases; Task 3 covers index, graph, local, and LangSmith verification.
- Every planned Korean clause has one English source page, and no unreviewed OCR is eligible for indexing.
