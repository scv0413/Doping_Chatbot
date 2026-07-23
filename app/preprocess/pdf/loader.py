import re
from pathlib import Path
from typing import Any

import fitz

from app.preprocess.ocr.fallback import PageExtractionResult, resolve_page_text
from app.preprocess.sources.manifest import load_source_manifest
from app.preprocess.sources.schemas import (
    DocumentChunk,
    DocumentMetadata,
    DocumentType,
    LayoutType,
    ProcessingStatus,
    TocEntry,
)


ROMAN_FOOTERS = {
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "vii",
    "viii",
    "ix",
    "x",
}

TOC_PATTERN = re.compile(r"^(.+?)\s*(?:\.|…|·){2,}\s*(\d+)(?:\s+.*)?$")
TOC_SEGMENT_PATTERN = re.compile(r"^.+?\s*(?:\.|…|·){2,}\s*\d+\s*")
BILINGUAL_SECTION_HEADING_PATTERN = re.compile(
    r"^(?P<english>.+?)\s+(?P<code>[A-Z]\d+(?:\.\d+)?)\s+(?P=code)\s+(?P<korean>[가-힣].*)$"
)
TOC_PAGE_KEYWORDS = {
    "TABLE OF CONTENTS",
    "CONTENTS",
    "목차",
}
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
PAGE_NUMBER_TAIL_PATTERN = re.compile(r"\n\s*\d{1,3}\s*\n\s*(?:\d{1,3}\s*){2,}\s*$")


def normalize_text(text: str) -> str:
    text = CONTROL_CHAR_PATTERN.sub("", text)
    return " ".join(text.split()).strip()


def is_year_only_noise(text: str) -> bool:
    cleaned = normalize_text(text)
    return cleaned.isdigit() and len(cleaned) == 4 and cleaned.startswith("20")


def is_footer_noise(text: str) -> bool:
    cleaned = normalize_text(text).lower()
    return cleaned in ROMAN_FOOTERS


def parse_toc_entry(text: str) -> dict[str, Any] | None:
    cleaned = normalize_text(text)
    match = TOC_PATTERN.match(cleaned)

    if not match:
        return None

    return {
        "title": match.group(1).strip(),
        "page": int(match.group(2)),
    }


def is_pure_toc_entry(text: str) -> bool:
    cleaned = normalize_text(text)
    match = TOC_PATTERN.match(cleaned)

    if not match:
        return False

    tail = cleaned[match.end(2) :].strip()
    return not tail


def remove_toc_segment(text: str) -> str:
    cleaned = normalize_text(text)
    return TOC_SEGMENT_PATTERN.sub("", cleaned).strip()


def is_toc_page_blocks(blocks: list[dict[str, Any]], min_toc_entries: int = 2) -> bool:
    combined_text = "\n".join(block["text"] for block in blocks if block["text"])
    upper_text = combined_text.upper()

    if any(keyword in upper_text for keyword in TOC_PAGE_KEYWORDS):
        return True

    toc_entry_count = sum(1 for block in blocks if parse_toc_entry(block["text"]))
    return toc_entry_count >= min_toc_entries


def extract_toc_entries_from_blocks(blocks: list[dict[str, Any]]) -> list[TocEntry]:
    entries: list[TocEntry] = []

    for block in blocks:
        entry = parse_toc_entry(block["text"])

        if not entry:
            continue

        entries.append(
            TocEntry(
                title=entry["title"],
                page=entry["page"],
            )
        )

    return entries


def should_skip_block(text: str, remove_footer: bool = True, remove_toc: bool = True) -> bool:
    cleaned = normalize_text(text)

    if not cleaned:
        return True

    if remove_footer and is_footer_noise(cleaned):
        return True

    if remove_toc and is_pure_toc_entry(cleaned):
        return True

    return False


def is_bottom_footer(block: dict[str, Any], page_height: float, margin: float = 40) -> bool:
    text = normalize_text(block["text"])

    if not text:
        return False

    if block["y0"] < page_height - margin:
        return False

    return text.isdigit() or is_footer_noise(text)


def is_page_edge_year_noise(
    block: dict[str, Any],
    page_height: float,
    top_margin: float = 90,
    bottom_margin: float = 70,
) -> bool:
    text = normalize_text(block["text"])

    if not is_year_only_noise(text):
        return False

    return block["y0"] <= top_margin or block["y0"] >= page_height - bottom_margin


def parse_pdf_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    parsed_blocks = []

    for block_index, block in enumerate(page.get_text("blocks")):
        x0, y0, x1, y1, text, *_ = block
        cleaned_text = normalize_text(text)

        parsed_blocks.append(
            {
                "block_index": block_index,
                "x0": float(x0),
                "y0": float(y0),
                "x1": float(x1),
                "y1": float(y1),
                "text": cleaned_text,
            }
        )

    return parsed_blocks


def parse_pdf_spans(page: fitz.Page) -> list[dict[str, Any]]:
    parsed_spans = []
    page_dict = page.get_text("dict")

    for block_index, block in enumerate(page_dict.get("blocks", [])):
        for line_index, line in enumerate(block.get("lines", [])):
            for span_index, span in enumerate(line.get("spans", [])):
                text = normalize_text(span.get("text", ""))

                if not text:
                    continue

                x0, y0, x1, y1 = span.get("bbox", [0, 0, 0, 0])

                parsed_spans.append(
                    {
                        "block_index": block_index,
                        "line_index": line_index,
                        "span_index": span_index,
                        "x0": float(x0),
                        "y0": float(y0),
                        "x1": float(x1),
                        "y1": float(y1),
                        "text": text,
                    }
                )

    return parsed_spans


def group_spans_into_lines(
    spans: list[dict[str, Any]],
    y_tolerance: float = 3,
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []

    for span in sorted(spans, key=lambda item: (item["y0"], item["x0"])):
        matching_line = None

        for line in lines:
            if abs(line["y0"] - span["y0"]) <= y_tolerance:
                matching_line = line
                break

        if matching_line is None:
            lines.append(
                {
                    "x0": span["x0"],
                    "y0": span["y0"],
                    "x1": span["x1"],
                    "y1": span["y1"],
                    "spans": [span],
                }
            )
            continue

        matching_line["spans"].append(span)
        matching_line["x0"] = min(matching_line["x0"], span["x0"])
        matching_line["y0"] = min(matching_line["y0"], span["y0"])
        matching_line["x1"] = max(matching_line["x1"], span["x1"])
        matching_line["y1"] = max(matching_line["y1"], span["y1"])

    normalized_lines = []
    for line in lines:
        sorted_spans = sorted(line["spans"], key=lambda item: item["x0"])
        text = normalize_text(" ".join(span["text"] for span in sorted_spans))

        if not text:
            continue

        normalized_lines.append(
            {
                "x0": line["x0"],
                "y0": line["y0"],
                "x1": line["x1"],
                "y1": line["y1"],
                "text": text,
            }
        )

    return sorted(normalized_lines, key=lambda item: (item["y0"], item["x0"]))


def parse_pdf_span_lines(page: fitz.Page) -> list[dict[str, Any]]:
    spans = parse_pdf_spans(page)
    return group_spans_into_lines(spans)


def sort_standard_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(blocks, key=lambda block: (block["y0"], block["x0"]))


def sort_column_blocks(
    blocks: list[dict[str, Any]],
    page_width: float,
    gutter: float = 20,
    heading_top_margin: float = 180,
) -> list[dict[str, Any]]:
    left_blocks = []
    right_blocks = []
    heading_blocks = []
    other_blocks = []
    center_x = page_width / 2

    for block in blocks:
        x0 = block["x0"]
        x1 = block["x1"]
        y0 = block["y0"]

        if x1 <= center_x - gutter:
            left_blocks.append(block)
        elif x0 >= center_x + gutter:
            right_blocks.append(block)
        elif y0 <= heading_top_margin:
            split_heading = split_bilingual_section_heading(block)

            if split_heading is None:
                heading_blocks.append(block)
            else:
                english_block, korean_block = split_heading
                left_blocks.append(english_block)
                right_blocks.append(korean_block)
        else:
            other_blocks.append(block)

    sorted_headings = sorted(heading_blocks, key=lambda block: (block["y0"], block["x0"]))
    sorted_other = sorted(other_blocks, key=lambda block: (block["y0"], block["x0"]))
    sorted_left = sorted(left_blocks, key=lambda block: block["y0"])
    sorted_right = sorted(right_blocks, key=lambda block: block["y0"])

    return sorted_headings + sorted_left + sorted_right + sorted_other


def split_bilingual_section_heading(
    block: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    text = normalize_text(block["text"])
    match = BILINGUAL_SECTION_HEADING_PATTERN.match(text)

    if not match:
        return None

    code = match.group("code")
    english_text = f"{code} {match.group('english').strip()}"
    korean_text = f"{code} {match.group('korean').strip()}"

    english_block = block.copy()
    korean_block = block.copy()
    english_block["text"] = english_text
    korean_block["text"] = korean_text

    return english_block, korean_block


def remove_page_number_tail(text: str) -> str:
    previous = None
    cleaned = text.strip()

    while previous != cleaned:
        previous = cleaned
        cleaned = PAGE_NUMBER_TAIL_PATTERN.sub("", cleaned).strip()

    return cleaned


def blocks_to_text(blocks: list[dict[str, Any]]) -> str:
    lines = [block["text"] for block in blocks if block["text"]]
    return remove_page_number_tail("\n".join(lines))


def clean_blocks(
    blocks: list[dict[str, Any]],
    page_height: float,
    remove_footer: bool = True,
    remove_toc: bool = True,
) -> list[dict[str, Any]]:
    cleaned_blocks = []

    for block in blocks:
        text = block["text"]

        if should_skip_block(text, remove_footer=remove_footer, remove_toc=remove_toc):
            continue

        if remove_footer and is_bottom_footer(block, page_height):
            continue

        if remove_footer and is_page_edge_year_noise(block, page_height):
            continue

        cleaned_blocks.append(block)

    return cleaned_blocks


def should_use_span_loader(metadata: DocumentMetadata) -> bool:
    return metadata.document_type == DocumentType.TESTING_STANDARD


def sort_blocks_for_layout(
    metadata: DocumentMetadata,
    blocks: list[dict[str, Any]],
    page_width: float,
) -> list[dict[str, Any]]:
    if (
        metadata.layout_type == LayoutType.MIXED_LANGUAGE
        or metadata.document_type == DocumentType.PROHIBITED_LIST
    ):
        return sort_column_blocks(blocks, page_width=page_width)

    return sort_standard_blocks(blocks)


def scan_toc_metadata(
    document: fitz.Document,
    metadata: DocumentMetadata,
    start_page: int,
    end_page: int,
) -> tuple[list[int], list[TocEntry]]:
    toc_pages: list[int] = [
        page for page in metadata.toc_pages if start_page <= page <= end_page
    ]
    toc_entries: list[TocEntry] = []
    toc_page_set = set(toc_pages)

    for page_number in range(start_page, end_page + 1):
        if page_number in toc_page_set:
            continue

        page = document.load_page(page_number - 1)
        blocks = parse_pdf_blocks(page)
        blocks = sort_blocks_for_layout(metadata, blocks, page_width=page.rect.width)

        if not is_toc_page_blocks(blocks):
            continue

        toc_pages.append(page_number)
        toc_page_set.add(page_number)
        toc_entries.extend(extract_toc_entries_from_blocks(blocks))

    return sorted(toc_pages), toc_entries


def count_hangul_chars(text: str) -> int:
    return sum(1 for char in text if "가" <= char <= "힣")


def count_suspicious_chars(text: str) -> int:
    suspicious_ranges = [
        ("\u1000", "\u109f"),  # Myanmar
        ("\u1200", "\u137f"),  # Ethiopic
        ("\u1400", "\u167f"),  # Canadian Aboriginal
    ]

    count = 0
    for char in text:
        if any(start <= char <= end for start, end in suspicious_ranges):
            count += 1

    return count


def is_low_quality_text(text: str, min_length: int = 100) -> bool:
    if len(text) < min_length:
        return False

    suspicious_count = count_suspicious_chars(text)
    hangul_count = count_hangul_chars(text)

    if suspicious_count > 20 and hangul_count < suspicious_count:
        return True

    return False


ISTI_SOURCE_ID = "wada_isti_2021_ko_en"

def should_use_korean_ocr_fallback(metadata: DocumentMetadata, page_number: int) -> bool:
    return metadata.source_id == ISTI_SOURCE_ID and page_number % 2 == 0


def provenance_update(result: PageExtractionResult | None) -> dict[str, Any]:
    if result is None:
        return {}

    return {
        "extraction_method": result.extraction_method,
        "quality_status": result.quality_report.status,
        "quality_reason": result.quality_report.reason,
        "ocr_language": result.ocr_language,
    }


def load_pdf_pages(
    metadata: DocumentMetadata,
    start_page: int = 1,
    end_page: int | None = None,
    remove_footer: bool = True,
    remove_toc: bool = True,
) -> list[DocumentChunk]:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    chunks: list[DocumentChunk] = []

    with fitz.open(pdf_path) as document:
        final_page = end_page or document.page_count
        toc_pages, toc_entries = scan_toc_metadata(
            document=document,
            metadata=metadata,
            start_page=start_page,
            end_page=final_page,
        )
        toc_page_set = set(toc_pages)

        for page_number in range(start_page, final_page + 1):
            if page_number in toc_page_set:
                continue

            page = document.load_page(page_number - 1)

            if should_use_span_loader(metadata):
                blocks = parse_pdf_span_lines(page)
            else:
                blocks = parse_pdf_blocks(page)

            page_height = page.rect.height
            blocks = clean_blocks(
                blocks,
                page_height=page_height,
                remove_footer=remove_footer,
                remove_toc=remove_toc,
            )
            blocks = sort_blocks_for_layout(metadata, blocks, page_width=page.rect.width)

            page_text = blocks_to_text(blocks)

            if not page_text:
                continue

            extraction_result = None
            if should_use_korean_ocr_fallback(metadata, page_number):
                extraction_result = resolve_page_text(
                    page,
                    text_layer_text=page_text,
                    expects_korean=True,
                )
                if extraction_result.text is None:
                    continue
                page_text = extraction_result.text
            elif is_low_quality_text(page_text):
                continue

            page_metadata = metadata.model_copy(
                update={
                    "page": page_number,
                    "toc_pages": toc_pages,
                    "toc_entries": toc_entries,
                    **provenance_update(extraction_result),
                }
            )

            chunks.append(
                DocumentChunk(
                    text=page_text,
                    metadata=page_metadata,
                )
            )

    return chunks


def inspect_pdf_page_loading(
    metadata: DocumentMetadata,
    start_page: int = 1,
    end_page: int | None = None,
    remove_footer: bool = True,
    remove_toc: bool = True,
) -> list[dict[str, Any]]:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    results: list[dict[str, Any]] = []

    with fitz.open(pdf_path) as document:
        final_page = end_page or document.page_count
        toc_pages, _ = scan_toc_metadata(
            document=document,
            metadata=metadata,
            start_page=start_page,
            end_page=final_page,
        )
        toc_page_set = set(toc_pages)

        for page_number in range(start_page, final_page + 1):
            if page_number in toc_page_set:
                results.append(
                    {
                        "page": page_number,
                        "status": "skipped",
                        "reason": "toc_page",
                        "char_count": 0,
                    }
                )
                continue

            page = document.load_page(page_number - 1)

            if should_use_span_loader(metadata):
                blocks = parse_pdf_span_lines(page)
            else:
                blocks = parse_pdf_blocks(page)

            blocks = clean_blocks(
                blocks,
                page_height=page.rect.height,
                remove_footer=remove_footer,
                remove_toc=remove_toc,
            )
            blocks = sort_blocks_for_layout(metadata, blocks, page_width=page.rect.width)
            page_text = blocks_to_text(blocks)

            if not page_text:
                results.append(
                    {
                        "page": page_number,
                        "status": "skipped",
                        "reason": "empty_text",
                        "char_count": 0,
                    }
                )
                continue

            extraction_result = None
            if should_use_korean_ocr_fallback(metadata, page_number):
                extraction_result = resolve_page_text(
                    page,
                    text_layer_text=page_text,
                    expects_korean=True,
                )
                if extraction_result.text is None:
                    results.append(
                        {
                            "page": page_number,
                            "status": "skipped",
                            "reason": extraction_result.quality_report.reason or "ocr_needs_review",
                            "char_count": extraction_result.quality_report.char_count,
                            **provenance_update(extraction_result),
                        }
                    )
                    continue
                page_text = extraction_result.text
            elif is_low_quality_text(page_text):
                results.append(
                    {
                        "page": page_number,
                        "status": "skipped",
                        "reason": "low_quality_text",
                        "char_count": len(page_text),
                    }
                )
                continue

            results.append(
                {
                    "page": page_number,
                    "status": "loaded",
                    "reason": "ok",
                    "char_count": len(page_text),
                    **provenance_update(extraction_result),
                }
            )

    return results


def load_manifest_pdf_pages(
    manifest_path: Path,
    include_needs_review: bool = True,
) -> list[DocumentChunk]:
    records = load_source_manifest(manifest_path)
    all_chunks: list[DocumentChunk] = []

    for record in records:
        if not include_needs_review and record.processing_status != ProcessingStatus.READY:
            continue

        chunks = load_pdf_pages(record)
        all_chunks.extend(chunks)

    return all_chunks


if __name__ == "__main__":
    manifest_path = Path("data/source_manifest.csv")
    records = load_source_manifest(manifest_path)
    preview_start_page = 1
    preview_end_page = 8
    preview_count = 8

    for record in records:
        print("=" * 80)
        print(record.source_id)
        print(record.title)

        chunks = load_pdf_pages(
            record,
            start_page=preview_start_page,
            end_page=preview_end_page,
        )

        print(f"loaded pages: {len(chunks)}")
        print(f"loaded page numbers: {[chunk.metadata.page for chunk in chunks]}")
        print("page decisions:")
        for decision in inspect_pdf_page_loading(
            record,
            start_page=preview_start_page,
            end_page=preview_end_page,
        ):
            print(decision)

        for chunk in chunks[:preview_count]:
            print("-" * 80)
            print(f"page: {chunk.metadata.page}")
            print(chunk.text[:800])
