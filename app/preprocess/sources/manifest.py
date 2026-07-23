import csv
from pathlib import Path

from app.preprocess.sources.schemas import (
    Authority,
    DocumentMetadata,
    DocumentType,
    Language,
    LayoutType,
    ProcessingStatus,
    SourceType,
)


def parse_page_list(value: str | None) -> list[int]:
    if not value:
        return []

    pages: list[int] = []

    for part in value.split(";"):
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            start, end = part.split("-", maxsplit=1)
            pages.extend(range(int(start), int(end) + 1))
            continue

        pages.append(int(part))

    return sorted(set(pages))


def load_source_manifest(manifest_path: Path) -> list[DocumentMetadata]:
    records: list[DocumentMetadata] = []

    with manifest_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            file_path = Path(row["file_path"])

            metadata = DocumentMetadata(
                source_id=row["source_id"],
                source_type=SourceType.PDF,
                title=row["title"],
                authority=Authority(row["authority"]),
                document_type=DocumentType(row["document_type"]),
                layout_type=LayoutType(row["layout_type"]),
                processing_status=ProcessingStatus(row["processing_status"]),
                file_name=file_path.name,
                file_path=file_path,
                language=Language(row["language"]),
                version=row.get("year") or None,
                toc_pages=parse_page_list(row.get("toc_pages")),
            )
            records.append(metadata)

    return records


def filter_ready_sources(records: list[DocumentMetadata]) -> list[DocumentMetadata]:
    return [
        record
        for record in records
        if record.processing_status == ProcessingStatus.READY
    ]
