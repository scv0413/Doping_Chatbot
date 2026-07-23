# ISTI English/Korean Section Alignment

## Purpose

`scripts/isti_section_alignment.py` creates a bounded review artifact for a
human reviewer. It finds hierarchical clause numbers such as `5.3.5` and
`13.1` in an English ISTI page and its Korean OCR page.

This is not a translation pipeline and does not create a bilingual retrieval
source.

## Matching Rule

- A candidate is recorded only when the same clause number occurs on exactly
  one supplied English page and exactly one supplied Korean OCR page.
- Repeated clause numbers or missing clause numbers are ambiguous and omitted.
- Adjacent odd/even page numbers alone never establish a match.

## Safety Boundary

The Korean OCR pages currently have `needs_review` quality. Every candidate is
therefore emitted with `review_only: true` and `usable_for_retrieval: false`.
The indexer does not read this artifact, and it must not be cited in chatbot
answers.

Use a candidate only to help a reviewer create or verify a separately
human-reviewed manual Korean source. That manual source follows the normal
manual preprocessing and indexing path after review.

## Local Run

```bash
uv run python scripts/isti_section_alignment.py \
  --pdf-path data/raw/pdf/wada/wada_isti_2021_ko_en.pdf \
  --page-pairs 83:84 163:164 \
  --output-path data/operations/isti_section_alignment_candidates.jsonl
```

The output path is intentionally outside `data/processed/`; it is a local
review artifact, not an indexing input.

## Human Review Handoff

Create a local review draft from the candidate artifact:

```bash
uv run python scripts/isti_manual_review_template.py \
  --candidates-path data/operations/isti_section_alignment_candidates.jsonl \
  --output-path data/operations/isti_korean_manual_review_draft.md
```

The generated file has `review-status: draft` and is never an indexing input.
After review, create a separate manual Korean source with its reviewer,
approval date, English-page citation, and reviewed Korean text. Only that
approved manual source may enter the normal manual preprocessing flow.
