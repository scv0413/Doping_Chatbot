import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.play.config import settings
from app.preprocess.manifest import load_source_manifest
from app.preprocess.pdf_loader import (
    inspect_pdf_page_loading,
    load_pdf_pages,
)
from app.preprocess.schemas import DocumentChunk


class PageRecord(BaseModel):
    text: str
    metadata: dict[str, Any]


class SkippedPageRecord(BaseModel):
    source_id: str
    title: str
    page: int
    reason: str
    char_count: int


def chunk_to_page_record(chunk: DocumentChunk) -> PageRecord:
    return PageRecord(
        text=chunk.text,
        metadata=chunk.metadata.model_dump(mode="json"),
    )


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json(ensure_ascii=False))
            file.write("\n")


def preprocess_manifest(
    manifest_path: Path = Path("data/source_manifest.csv"),
    pages_output_path: Path | None = None,
    skipped_output_path: Path | None = None,
) -> None:
    pages_output_path = pages_output_path or settings.processed_data_dir / "pages.jsonl"
    skipped_output_path = skipped_output_path or settings.processed_data_dir / "skipped_pages.jsonl"

    sources = load_source_manifest(manifest_path)

    page_records: list[PageRecord] = []
    skipped_records: list[SkippedPageRecord] = []

    for source in sources:
        chunks = load_pdf_pages(source)
        page_records.extend(chunk_to_page_record(chunk) for chunk in chunks)

        decisions = inspect_pdf_page_loading(source)

        for decision in decisions:
            if decision["status"] != "skipped":
                continue

            skipped_records.append(
                SkippedPageRecord(
                    source_id=source.source_id,
                    title=source.title,
                    page=decision["page"],
                    reason=decision["reason"],
                    char_count=decision["char_count"],
                )
            )

    write_jsonl(pages_output_path, page_records)
    write_jsonl(skipped_output_path, skipped_records)

    print(f"saved pages: {len(page_records)} -> {pages_output_path}")
    print(f"saved skipped pages: {len(skipped_records)} -> {skipped_output_path}")


if __name__ == "__main__":
    preprocess_manifest()