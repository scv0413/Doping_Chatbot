import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings

MANUAL_SOURCE_ID = "field_response_manual"
MANUAL_TITLE = "현장 대응 매뉴얼"
SECTION_HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)


class ManualChunkRecord(BaseModel):
    text: str = Field(min_length=1)
    metadata: dict[str, Any]


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json(ensure_ascii=False))
            file.write("\n")


def normalize_manual_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_manual_sections(markdown_text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_HEADING_PATTERN.finditer(markdown_text))
    sections: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        section_text = normalize_manual_text(markdown_text[start:end])

        if section_text and title != "목적":
            sections.append((title, section_text))

    return sections


def build_manual_chunk_id(section_index: int) -> str:
    return f"{MANUAL_SOURCE_ID}:s{section_index}:c0"


def load_manual_chunks(
    manual_path: Path | None = None,
) -> list[ManualChunkRecord]:
    manual_path = manual_path or Path("app/chat/docs/field-response-manual.md")
    markdown_text = manual_path.read_text(encoding="utf-8")
    sections = split_manual_sections(markdown_text)
    chunks: list[ManualChunkRecord] = []

    for index, (section_title, section_text) in enumerate(sections, start=1):
        metadata = {
            "source_id": MANUAL_SOURCE_ID,
            "source_type": "manual",
            "title": MANUAL_TITLE,
            "authority": "manual",
            "document_type": "other",
            "layout_type": "standard",
            "processing_status": "ready",
            "file_name": manual_path.name,
            "file_path": str(manual_path),
            "page": None,
            "section": section_title,
            "language": "ko",
            "chunk_index": 0,
            "chunk_id": build_manual_chunk_id(index),
            "chunk_char_count": len(section_text),
        }
        chunks.append(ManualChunkRecord(text=section_text, metadata=metadata))

    return chunks


def build_manual_chunks(
    manual_path: Path | None = None,
    output_path: Path | None = None,
) -> None:
    output_path = output_path or settings.processed_data_dir / "manual_chunks.jsonl"
    chunks = load_manual_chunks(manual_path=manual_path)
    write_jsonl(output_path, chunks)

    print(f"loaded manual sections: {len(chunks)}")
    print(f"saved manual chunks: {len(chunks)} -> {output_path}")


if __name__ == "__main__":
    build_manual_chunks()
