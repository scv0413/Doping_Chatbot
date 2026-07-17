import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.chat.config import settings


DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 120
MIN_SENTENCE_SPLIT_SIZE = 450
SENTENCE_END_PATTERN = re.compile(r"[.!?。！？]|(?:다|요|함|됨|음|임)[.)]?", re.MULTILINE)


class PageRecord(BaseModel):
    text: str
    metadata: dict[str, Any]


class ChunkRecord(BaseModel):
    text: str = Field(min_length=1)
    metadata: dict[str, Any]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    return records


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json(ensure_ascii=False))
            file.write("\n")


def split_into_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)

    cleaned: list[str] = []
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        paragraph = re.sub(r"[ \t]+", " ", paragraph)

        if paragraph:
            cleaned.append(paragraph)

    return cleaned


def find_sentence_boundary(text: str, start: int, max_end: int) -> int:
    min_end = min(start + MIN_SENTENCE_SPLIT_SIZE, max_end)
    window = text[start:max_end]
    candidates: list[int] = []

    for match in SENTENCE_END_PATTERN.finditer(window):
        boundary = start + match.end()

        if boundary >= min_end:
            candidates.append(boundary)

    if candidates:
        return candidates[-1]

    newline_boundary = text.rfind("\n", min_end, max_end)

    if newline_boundary != -1:
        return newline_boundary

    space_boundary = text.rfind(" ", min_end, max_end)

    if space_boundary != -1:
        return space_boundary

    return max_end


def split_long_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        max_end = min(start + chunk_size, len(text))
        end = find_sentence_boundary(text, start, max_end)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if max_end >= len(text):
            break

        next_start = max(end - chunk_overlap, start + 1)
        start = next_start

    return chunks


def chunk_page(
    page: PageRecord,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[ChunkRecord]:
    paragraphs = split_into_paragraphs(page.text)

    chunks: list[ChunkRecord] = []
    buffer = ""

    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph

        if len(candidate) <= chunk_size:
            buffer = candidate
            continue

        if buffer:
            chunks.append(
                ChunkRecord(
                    text=buffer,
                    metadata=page.metadata.copy(),
                )
            )

        if len(paragraph) > chunk_size:
            for part in split_long_text(paragraph, chunk_size, chunk_overlap):
                chunks.append(
                    ChunkRecord(
                        text=part,
                        metadata=page.metadata.copy(),
                    )
                )
            buffer = ""
        else:
            buffer = paragraph

    if buffer:
        chunks.append(
            ChunkRecord(
                text=buffer,
                metadata=page.metadata.copy(),
            )
        )

    return chunks


def build_chunk_id(metadata: dict[str, Any], chunk_index: int) -> str:
    source_id = metadata.get("source_id", "unknown_source")
    page = metadata.get("page", "unknown_page")
    return f"{source_id}:p{page}:c{chunk_index}"


def add_chunk_metadata(chunks: list[ChunkRecord]) -> list[ChunkRecord]:
    enriched_chunks: list[ChunkRecord] = []

    for index, chunk in enumerate(chunks):
        metadata = chunk.metadata.copy()
        metadata["chunk_index"] = index
        metadata["chunk_id"] = build_chunk_id(metadata, index)
        metadata["chunk_char_count"] = len(chunk.text)

        enriched_chunks.append(
            ChunkRecord(
                text=chunk.text,
                metadata=metadata,
            )
        )

    return enriched_chunks


def chunk_pages(
    pages_path: Path | None = None,
    chunks_output_path: Path | None = None,
) -> None:
    pages_path = pages_path or settings.processed_data_dir / "pages.jsonl"
    chunks_output_path = chunks_output_path or settings.processed_data_dir / "chunks.jsonl"

    raw_pages = read_jsonl(pages_path)

    all_chunks: list[ChunkRecord] = []

    for raw_page in raw_pages:
        page = PageRecord.model_validate(raw_page)
        page_chunks = chunk_page(page)
        page_chunks = add_chunk_metadata(page_chunks)
        all_chunks.extend(page_chunks)

    write_jsonl(chunks_output_path, all_chunks)

    print(f"loaded pages: {len(raw_pages)}")
    print(f"saved chunks: {len(all_chunks)} -> {chunks_output_path}")


if __name__ == "__main__":
    chunk_pages()