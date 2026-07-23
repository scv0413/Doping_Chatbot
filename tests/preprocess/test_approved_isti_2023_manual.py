from pathlib import Path

import pytest

from app.preprocess.manual_loader import (
    load_approved_manual_chunks,
    split_approved_manual_sections,
)


MANUAL_PATH = Path("docs/architecture/wada-isti-2023-korean-reviewed.md")


def test_approved_isti_2023_manual_uses_english_source_without_ocr_page() -> None:
    chunks = load_approved_manual_chunks(MANUAL_PATH)

    assert len(chunks) == 9
    assert chunks[0].metadata["source_id"] == "wada_isti_2023_ko_human_reviewed"
    assert chunks[0].metadata["official_source_id"] == "wada_isti_2023_en"
    assert chunks[0].metadata["official_source_page"] == 42
    assert chunks[0].metadata["korean_ocr_page"] is None
    assert "통지 방법과 시점" in chunks[0].text


def test_approved_manual_still_requires_english_source_page() -> None:
    with pytest.raises(ValueError, match="english-source-page"):
        split_approved_manual_sections("## 5.3.5\n검수한 한국어 문장")


def test_approved_isti_2023_manual_covers_notification_rights_and_delay_rules() -> None:
    chunks = load_approved_manual_chunks(MANUAL_PATH)
    sections = {chunk.metadata["section"]: chunk for chunk in chunks}

    assert {"5.4.1", "5.4.2", "5.4.3", "5.4.4", "5.4.5"} <= sections.keys()
    assert sections["5.4.1"].metadata["official_source_page"] == 43
    assert sections["5.4.2"].metadata["official_source_page"] == 44
    assert sections["5.4.5"].metadata["official_source_page"] == 45
    assert "지속 관찰" in sections["5.4.4"].text
