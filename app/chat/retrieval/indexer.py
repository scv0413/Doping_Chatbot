import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.core.config import settings
from app.chat.retrieval.vector_store import (
    count_vector_store_documents,
    get_chroma_persist_directory,
    get_vector_store,
    to_chroma_metadata,
)

DEFAULT_BATCH_SIZE = 64
DEFAULT_CHUNK_FILE_NAMES = ("chunks.jsonl", "manual_chunks.jsonl")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    return records


def batched(records: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [records[index : index + batch_size] for index in range(0, len(records), batch_size)]


def get_default_chunk_paths() -> list[Path]:
    return [
        settings.processed_data_dir / file_name
        for file_name in DEFAULT_CHUNK_FILE_NAMES
        if (settings.processed_data_dir / file_name).exists()
    ]


def load_chunk_records(chunks_paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for chunks_path in chunks_paths:
        path_records = read_jsonl(chunks_path)
        print(f"loaded {len(path_records)} chunks from {chunks_path}")
        records.extend(path_records)

    return records


def validate_chunk_records(records: list[dict[str, Any]]) -> None:
    chunk_ids = [record["metadata"]["chunk_id"] for record in records]
    duplicate_count = len(chunk_ids) - len(set(chunk_ids))

    if duplicate_count:
        raise ValueError(f"Duplicate chunk_id count: {duplicate_count}")


def records_to_documents(records: list[dict[str, Any]]) -> list[Document]:
    return [
        Document(
            page_content=record["text"],
            metadata=to_chroma_metadata(record["metadata"]),
        )
        for record in records
    ]


def index_chunks(
    chunks_path: Path | None = None,
    chunks_paths: list[Path] | None = None,
    reset_collection: bool = True,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    if chunks_path is not None and chunks_paths is not None:
        raise ValueError("Use either chunks_path or chunks_paths, not both.")

    if chunks_path is not None:
        resolved_chunk_paths = [chunks_path]
    else:
        resolved_chunk_paths = chunks_paths or get_default_chunk_paths()

    if not resolved_chunk_paths:
        raise FileNotFoundError("No chunk JSONL files found for indexing.")

    records = load_chunk_records(resolved_chunk_paths)
    validate_chunk_records(records)

    vector_store = get_vector_store(collection_metadata={"hnsw:space": "cosine"})
    if reset_collection:
        vector_store.reset_collection()

    for batch in batched(records, batch_size):
        ids = [record["metadata"]["chunk_id"] for record in batch]
        documents = records_to_documents(batch)
        vector_store.add_documents(
            documents=documents,
            ids=ids,
        )

    print(f"total loaded chunks: {len(records)}")
    print(f"indexed chunks: {count_vector_store_documents(vector_store)}")
    print(f"collection: {settings.chroma_collection_name}")
    print(f"path: {get_chroma_persist_directory(create=False)}")


if __name__ == "__main__":
    index_chunks()
