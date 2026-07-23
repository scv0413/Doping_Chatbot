from app.chat.domain.retrieval.indexer import DEFAULT_CHUNK_FILE_NAMES, validate_chunk_records

import pytest


def test_default_index_inputs_exclude_review_only_alignment_artifacts() -> None:
    assert DEFAULT_CHUNK_FILE_NAMES == (
        "chunks.jsonl",
        "manual_chunks.jsonl",
        "approved_manual_chunks.jsonl",
    )
    assert "isti_section_alignment_candidates.jsonl" not in DEFAULT_CHUNK_FILE_NAMES


def test_indexer_rejects_human_reviewed_manual_without_approval_metadata() -> None:
    records = [
        {
            "text": "검수되었다고 주장하는 한국어 내용",
            "metadata": {
                "chunk_id": "wada_isti_ko_human_reviewed:5.3.5:c0",
                "source_id": "wada_isti_ko_human_reviewed",
                "source_type": "manual",
            },
        }
    ]

    with pytest.raises(ValueError, match="approved"):
        validate_chunk_records(records)


def test_indexer_accepts_complete_human_reviewed_manual_metadata() -> None:
    records = [
        {
            "text": "검수된 한국어 안내문",
            "metadata": {
                "chunk_id": "wada_isti_ko_human_reviewed:5.3.5:c0",
                "source_id": "wada_isti_ko_human_reviewed",
                "source_type": "manual",
                "review_status": "approved",
                "reviewed_by": "reviewer-001",
                "reviewed_at": "2026-07-23",
                "official_source_id": "wada_isti_2021_ko_en",
                "official_source_page": 83,
            },
        }
    ]

    validate_chunk_records(records)
