import re
import tomllib
from datetime import date
from typing import Literal
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
    manual_path = manual_path or Path("docs/architecture/field-response-manual.md")
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

APPROVED_MANUAL_FRONT_MATTER_DELIMITER = "+++"
APPROVED_MANUAL_SECTION_PATTERN = re.compile(r"^##\s+([\d]+(?:\.[\d]+)+)\s*$", re.MULTILINE)
ENGLISH_SOURCE_PAGE_PATTERN = re.compile(r"<!--\s*english-source-page:\s*(\d+)\s*-->")
KOREAN_OCR_PAGE_PATTERN = re.compile(r"<!--\s*korean-ocr-page:\s*(\d+)\s*-->")
REVIEW_PLACEHOLDER_PATTERN = re.compile(r"<!--\s*Human reviewer:", re.IGNORECASE)


class ApprovedManualFrontMatter(BaseModel):
    source_id: str
    title: str
    review_status: Literal["approved"]
    reviewed_by: str = Field(min_length=1)
    reviewed_at: date
    official_source_id: str = Field(min_length=1)


def load_approved_manual_chunks(manual_path: Path) -> list[ManualChunkRecord]:
    """Load only a fully human-approved Korean manual with page-level traceability."""

    front_matter, body = parse_approved_manual_document(manual_path.read_text(encoding="utf-8"))
    sections = split_approved_manual_sections(body)
    chunks: list[ManualChunkRecord] = []

    for section_number, section_text, english_page, korean_ocr_page in sections:
        metadata = {
            "source_id": front_matter.source_id,
            "source_type": "manual",
            "title": front_matter.title,
            "authority": "manual",
            "document_type": "testing_standard",
            "layout_type": "standard",
            "processing_status": "ready",
            "file_name": manual_path.name,
            "file_path": str(manual_path),
            "page": english_page,
            "section": section_number,
            "language": "ko",
            "source_language": "ko",
            "review_status": front_matter.review_status,
            "reviewed_by": front_matter.reviewed_by,
            "reviewed_at": front_matter.reviewed_at.isoformat(),
            "official_source_id": front_matter.official_source_id,
            "official_source_page": english_page,
            "korean_ocr_page": korean_ocr_page,
            "chunk_index": 0,
            "chunk_id": f"{front_matter.source_id}:{section_number}:c0",
            "chunk_char_count": len(section_text),
        }
        chunks.append(ManualChunkRecord(text=section_text, metadata=metadata))

    return chunks


def parse_approved_manual_document(markdown_text: str) -> tuple[ApprovedManualFrontMatter, str]:
    normalized = markdown_text.replace("\r\n", "\n")
    if not normalized.startswith(f"{APPROVED_MANUAL_FRONT_MATTER_DELIMITER}\n"):
        raise ValueError("Approved manual requires TOML front matter beginning with +++.")

    _, front_matter_text, body = normalized.split(APPROVED_MANUAL_FRONT_MATTER_DELIMITER, maxsplit=2)
    try:
        front_matter = ApprovedManualFrontMatter.model_validate(tomllib.loads(front_matter_text))
    except Exception as error:
        raise ValueError(f"Approved manual front matter must declare review_status = 'approved': {error}") from error

    return front_matter, body.strip()


def split_approved_manual_sections(markdown_text: str) -> list[tuple[str, str, int, int]]:
    matches = list(APPROVED_MANUAL_SECTION_PATTERN.finditer(markdown_text))
    if not matches:
        raise ValueError("Approved manual requires at least one numbered ## section.")

    sections: list[tuple[str, str, int, int]] = []
    for index, match in enumerate(matches):
        section_number = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        section_text = markdown_text[start:end].strip()
        english_page = _extract_required_page(ENGLISH_SOURCE_PAGE_PATTERN, section_text, "english-source-page")
        korean_ocr_page = _extract_required_page(KOREAN_OCR_PAGE_PATTERN, section_text, "korean-ocr-page")
        cleaned_text = ENGLISH_SOURCE_PAGE_PATTERN.sub("", section_text)
        cleaned_text = KOREAN_OCR_PAGE_PATTERN.sub("", cleaned_text).strip()

        if not cleaned_text or REVIEW_PLACEHOLDER_PATTERN.search(cleaned_text):
            raise ValueError(f"Section {section_number} requires verified Korean text without a review placeholder.")

        sections.append((section_number, cleaned_text, english_page, korean_ocr_page))

    return sections


def _extract_required_page(pattern: re.Pattern[str], text: str, marker_name: str) -> int:
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Approved manual section requires <!-- {marker_name}: PAGE -->.")
    return int(match.group(1))


def build_approved_manual_chunks(
    manual_path: Path,
    output_path: Path | None = None,
) -> None:
    output_path = output_path or settings.processed_data_dir / "approved_manual_chunks.jsonl"
    chunks = load_approved_manual_chunks(manual_path)
    write_jsonl(output_path, chunks)
    print(f"loaded approved manual sections: {len(chunks)}")
    print(f"saved approved manual chunks: {len(chunks)} -> {output_path}")
