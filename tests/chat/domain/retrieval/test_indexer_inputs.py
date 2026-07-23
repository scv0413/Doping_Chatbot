from app.chat.domain.retrieval.indexer import DEFAULT_CHUNK_FILE_NAMES


def test_default_index_inputs_exclude_review_only_alignment_artifacts() -> None:
    assert DEFAULT_CHUNK_FILE_NAMES == (
        "chunks.jsonl",
        "manual_chunks.jsonl",
        "approved_manual_chunks.jsonl",
    )
    assert "isti_section_alignment_candidates.jsonl" not in DEFAULT_CHUNK_FILE_NAMES
