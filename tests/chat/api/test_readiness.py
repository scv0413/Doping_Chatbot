from pathlib import Path

import chromadb

from app.chat.api.readiness import build_readiness_response
from app.chat.config import settings
from app.chat.retrieval.indexer import DEFAULT_CHUNK_FILE_NAMES


def test_readiness_reports_not_ready_when_chunk_files_are_missing(tmp_path: Path, monkeypatch) -> None:
    processed_dir = tmp_path / "processed"
    index_dir = tmp_path / "indexes"
    processed_dir.mkdir()
    (index_dir / "chroma").mkdir(parents=True)

    monkeypatch.setattr(settings, "processed_data_dir", processed_dir)
    monkeypatch.setattr(settings, "index_dir", index_dir)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    response = build_readiness_response()

    checks = {check.name: check for check in response.checks}
    assert response.status == "not_ready"
    assert checks["processed_chunks"].ready is False
    assert "missing chunk files" in checks["processed_chunks"].detail


def test_readiness_reports_ready_for_local_runtime_dependencies(tmp_path: Path, monkeypatch) -> None:
    processed_dir = tmp_path / "processed"
    index_dir = tmp_path / "indexes"
    chroma_dir = index_dir / "chroma"
    processed_dir.mkdir()
    chroma_dir.mkdir(parents=True)

    chunks_path = processed_dir / DEFAULT_CHUNK_FILE_NAMES[0]
    chunks_path.write_text(
        '{"text":"sample","metadata":{"chunk_id":"sample:p1:c0"}}\n',
        encoding="utf-8",
    )

    collection_name = "readiness_test_collection"
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(collection_name)
    collection.add(
        ids=["sample:p1:c0"],
        documents=["S0 비승인 약물"],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[{"source_id": "sample"}],
    )

    monkeypatch.setattr(settings, "processed_data_dir", processed_dir)
    monkeypatch.setattr(settings, "index_dir", index_dir)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "chroma_collection_name", collection_name)

    response = build_readiness_response()

    checks = {check.name: check for check in response.checks}
    assert response.status == "ready"
    assert checks["processed_chunks"].ready is True
    assert checks["chroma_collection"].ready is True
    assert checks["openai_api_key"].ready is True
    assert checks["runtime_import"].ready is True
    assert checks["runtime_policy_import"].ready is True
