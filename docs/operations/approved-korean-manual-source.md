# Approved Korean Manual Source Contract

## Purpose

An ISTI Korean manual can become a retrieval source only after a human reviewer
has verified its Korean text against the official English original. OCR is a
navigation aid, not the source of truth.

## Required Markdown Structure

Use TOML front matter followed by numbered clause sections:

```markdown
+++
source_id = "wada_isti_ko_human_reviewed"
title = "WADA ISTI Korean Human-Reviewed Guide"
review_status = "approved"
reviewed_by = "reviewer-identifier"
reviewed_at = "2026-07-23"
official_source_id = "wada_isti_2021_ko_en"
+++

## 5.3.5
<!-- english-source-page: 83 -->
<!-- korean-ocr-page: 84 -->
Human-reviewed Korean text goes here.
```

`review_status` must be exactly `approved`. Every clause must include both the
official English source page and the Korean OCR page used during review. Draft
markers or missing page citations cause preprocessing to fail.

## Build and Index

```bash
uv run python scripts/build_approved_manual.py \
  --manual-path docs/architecture/wada-isti-korean-reviewed.md
```

This writes `data/processed/approved_manual_chunks.jsonl`. The standard indexer
includes that file only when it exists. Alignment candidate JSONL files and
review drafts are never index inputs.

## Review Responsibility

The reviewer is responsible for making the Korean wording faithful to the
official English page. The resulting manual is a reviewed explanatory source,
not an official WADA Korean publication; chatbot answers should preserve the
official English citation.
