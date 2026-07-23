from pathlib import Path

import pytest

from app.preprocess.manual_loader import load_approved_manual_chunks


def test_loads_human_approved_korean_manual_with_english_citation(tmp_path: Path) -> None:
    manual_path = tmp_path / "isti_ko_reviewed.md"
    manual_path.write_text(
        """+++
source_id = "wada_isti_ko_human_reviewed"
title = "WADA ISTI Korean Human-Reviewed Guide"
review_status = "approved"
reviewed_by = "reviewer-001"
reviewed_at = "2026-07-23"
official_source_id = "wada_isti_2021_ko_en"
+++

## 5.3.5
<!-- english-source-page: 83 -->
<!-- korean-ocr-page: 84 -->
검수된 한국어 안내문입니다.
""",
        encoding="utf-8",
    )

    chunks = load_approved_manual_chunks(manual_path)

    assert len(chunks) == 1
    assert chunks[0].metadata["chunk_id"] == "wada_isti_ko_human_reviewed:5.3.5:c0"
    assert chunks[0].metadata["official_source_page"] == 83
    assert chunks[0].metadata["korean_ocr_page"] == 84
    assert chunks[0].metadata["review_status"] == "approved"
    assert chunks[0].metadata["reviewed_by"] == "reviewer-001"


def test_rejects_draft_or_missing_section_citation(tmp_path: Path) -> None:
    manual_path = tmp_path / "draft.md"
    manual_path.write_text(
        """+++
source_id = "wada_isti_ko_human_reviewed"
title = "draft"
review_status = "draft"
reviewed_by = "reviewer-001"
reviewed_at = "2026-07-23"
official_source_id = "wada_isti_2021_ko_en"
+++

## 5.3.5
검수 전 초안입니다.
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="approved"):
        load_approved_manual_chunks(manual_path)


def test_rejects_approved_section_without_english_page_citation(tmp_path: Path) -> None:
    manual_path = tmp_path / "missing-citation.md"
    manual_path.write_text(
        """+++
source_id = "wada_isti_ko_human_reviewed"
title = "approved manual"
review_status = "approved"
reviewed_by = "reviewer-001"
reviewed_at = "2026-07-23"
official_source_id = "wada_isti_2021_ko_en"
+++

## 5.3.5
<!-- korean-ocr-page: 84 -->
검수된 한국어 안내문입니다.
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="english-source-page"):
        load_approved_manual_chunks(manual_path)
