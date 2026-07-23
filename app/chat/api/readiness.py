from pathlib import Path
from typing import Callable

import chromadb
from pydantic import BaseModel, Field

from app.core.config import settings
from app.chat.retrieval.indexer import DEFAULT_CHUNK_FILE_NAMES
from app.chat.retrieval.vector_store import get_chroma_persist_directory


class ReadinessCheck(BaseModel):
    name: str
    ready: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    checks: list[ReadinessCheck] = Field(default_factory=list)


CheckBuilder = Callable[[], ReadinessCheck]


def build_readiness_response() -> ReadinessResponse:
    checks = [
        check_directory("processed_data_dir", settings.processed_data_dir),
        check_processed_chunks(),
        check_directory("index_dir", settings.index_dir),
        check_directory("chroma_directory", Path(get_chroma_persist_directory(create=False))),
        check_chroma_collection(),
        check_openai_api_key(),
        check_runtime_import(),
        check_runtime_policy_import(),
    ]
    status = "ready" if all(check.ready for check in checks) else "not_ready"
    return ReadinessResponse(status=status, checks=checks)


def check_directory(name: str, path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck(name=name, ready=False, detail=f"missing: {path}")
    if not path.is_dir():
        return ReadinessCheck(name=name, ready=False, detail=f"not a directory: {path}")
    return ReadinessCheck(name=name, ready=True, detail=str(path))


def check_processed_chunks() -> ReadinessCheck:
    existing_paths = [
        settings.processed_data_dir / file_name
        for file_name in DEFAULT_CHUNK_FILE_NAMES
        if (settings.processed_data_dir / file_name).exists()
    ]
    if not existing_paths:
        expected = ", ".join(DEFAULT_CHUNK_FILE_NAMES)
        return ReadinessCheck(
            name="processed_chunks",
            ready=False,
            detail=f"missing chunk files in {settings.processed_data_dir}: {expected}",
        )

    total_lines = 0
    details: list[str] = []
    for path in existing_paths:
        line_count = count_non_empty_lines(path)
        total_lines += line_count
        details.append(f"{path.name}={line_count}")

    if total_lines == 0:
        return ReadinessCheck(
            name="processed_chunks",
            ready=False,
            detail=f"empty chunk files: {', '.join(details)}",
        )

    return ReadinessCheck(
        name="processed_chunks",
        ready=True,
        detail=f"total_chunks={total_lines}; " + ", ".join(details),
    )


def count_non_empty_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def check_chroma_collection() -> ReadinessCheck:
    persist_directory = Path(get_chroma_persist_directory(create=False))
    if not persist_directory.exists():
        return ReadinessCheck(
            name="chroma_collection",
            ready=False,
            detail=f"missing chroma directory: {persist_directory}",
        )

    try:
        client = chromadb.PersistentClient(path=str(persist_directory))
        collection = client.get_collection(settings.chroma_collection_name)
        count = collection.count()
    except Exception as exc:
        return ReadinessCheck(
            name="chroma_collection",
            ready=False,
            detail=f"unavailable: {type(exc).__name__}: {exc}",
        )

    if count <= 0:
        return ReadinessCheck(
            name="chroma_collection",
            ready=False,
            detail=f"empty collection: {settings.chroma_collection_name}",
        )

    return ReadinessCheck(
        name="chroma_collection",
        ready=True,
        detail=f"{settings.chroma_collection_name} count={count}",
    )


def check_openai_api_key() -> ReadinessCheck:
    if not settings.openai_api_key:
        return ReadinessCheck(
            name="openai_api_key",
            ready=False,
            detail="missing OPENAI_API_KEY",
        )
    return ReadinessCheck(name="openai_api_key", ready=True, detail="configured")


def check_runtime_import() -> ReadinessCheck:
    try:
        from app.chat.runtime import run_chat  # noqa: PLC0415
    except Exception as exc:
        return ReadinessCheck(
            name="runtime_import",
            ready=False,
            detail=f"unavailable: {type(exc).__name__}: {exc}",
        )

    return ReadinessCheck(
        name="runtime_import",
        ready=callable(run_chat),
        detail="run_chat importable",
    )


def check_runtime_policy_import() -> ReadinessCheck:
    try:
        from app.chat.policy.runtime_policy import decide_runtime_policy  # noqa: PLC0415
    except Exception as exc:
        return ReadinessCheck(
            name="runtime_policy_import",
            ready=False,
            detail=f"unavailable: {type(exc).__name__}: {exc}",
        )

    return ReadinessCheck(
        name="runtime_policy_import",
        ready=callable(decide_runtime_policy),
        detail="decide_runtime_policy importable",
    )
