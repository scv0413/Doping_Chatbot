from pathlib import Path
import re
import fitz

from app.preprocess.sources.manifest import load_source_manifest
from app.preprocess.sources.schemas import DocumentMetadata


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


def is_footer_noise(text: str) -> bool:
    cleaned = " ".join(text.split()).strip().lower()
    return cleaned in ROMAN_FOOTERS


def inspect_pdf(metadata: DocumentMetadata, sample_pages: int = 2) -> dict:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        samples = []

        for page_index in range(min(sample_pages, page_count)):
            page = document.load_page(page_index)
            text = page.get_text("text").strip()

            samples.append(
                {
                    "page": page_index + 1,
                    "char_count": len(text),
                    "text_preview": text[:500],
                }
            )

    return {
        "source_id": metadata.source_id,
        "title": metadata.title,
        "file_path": str(pdf_path),
        "page_count": page_count,
        "samples": samples,
    }


def inspect_manifest_pdfs(manifest_path: Path) -> list[dict]:
    records = load_source_manifest(manifest_path)
    return [inspect_pdf(record) for record in records]


def inspect_pdf_blocks(metadata: DocumentMetadata, page_number: int = 1) -> list[dict]:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    with fitz.open(pdf_path) as document:
        page = document.load_page(page_number - 1)
        blocks = page.get_text("blocks")

        results = []
        for block_index, block in enumerate(blocks):
            x0, y0, x1, y1, text, *_ = block
            cleaned_text = " ".join(text.split())

            results.append(
                {
                    "block_index": block_index,
                    "bbox": {
                        "x0": round(x0, 2),
                        "y0": round(y0, 2),
                        "x1": round(x1, 2),
                        "y1": round(y1, 2),
                    },
                    "char_count": len(cleaned_text),
                    "text_preview": cleaned_text[:200],
                }
            )

    return results


def inspect_sorted_pdf_blocks(
    metadata: DocumentMetadata,
    page_number: int = 1,
    remove_footer: bool = True,
) -> list[dict]:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    with fitz.open(pdf_path) as document:
        page = document.load_page(page_number - 1)
        blocks = page.get_text("blocks")

        parsed_blocks = []
        for block_index, block in enumerate(blocks):
            x0, y0, x1, y1, text, *_ = block
            cleaned_text = " ".join(text.split()).strip()

            if not cleaned_text:
                continue

            if remove_footer and is_footer_noise(cleaned_text):
                continue

            parsed_blocks.append(
                {
                    "block_index": block_index,
                    "x0": round(x0, 2),
                    "y0": round(y0, 2),
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "char_count": len(cleaned_text),
                    "text_preview": cleaned_text[:200],
                }
            )

    return sorted(parsed_blocks, key=lambda item: (item["y0"], item["x0"]))


def inspect_column_sorted_pdf_blocks(
    metadata: DocumentMetadata,
    page_number: int = 1,
    left_x_range: tuple[float, float] = (80, 400),
    right_x_min: float = 600,
    remove_footer: bool = True,
) -> dict:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    left_blocks = []
    right_blocks = []
    other_blocks = []

    with fitz.open(pdf_path) as document:
        page = document.load_page(page_number - 1)
        blocks = page.get_text("blocks")

        for block_index, block in enumerate(blocks):
            x0, y0, x1, y1, text, *_ = block
            cleaned_text = " ".join(text.split()).strip()

            if not cleaned_text:
                continue

            if remove_footer and is_footer_noise(cleaned_text):
                continue

            item = {
                "block_index": block_index,
                "x0": round(x0, 2),
                "y0": round(y0, 2),
                "x1": round(x1, 2),
                "y1": round(y1, 2),
                "char_count": len(cleaned_text),
                "text_preview": cleaned_text[:200],
            }

            if left_x_range[0] <= x0 <= left_x_range[1]:
                left_blocks.append(item)
            elif x0 >= right_x_min:
                right_blocks.append(item)
            else:
                other_blocks.append(item)

    return {
        "source_id": metadata.source_id,
        "page_number": page_number,
        "left_blocks": sorted(left_blocks, key=lambda item: item["y0"]),
        "right_blocks": sorted(right_blocks, key=lambda item: item["y0"]),
        "other_blocks": sorted(other_blocks, key=lambda item: (item["y0"], item["x0"])),
    }

def inspect_pdf_spans(metadata: DocumentMetadata, page_number: int = 1) -> list[dict]:
    if metadata.file_path is None:
        raise ValueError(f"file_path is missing: {metadata.source_id}")

    pdf_path = metadata.file_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    results = []

    with fitz.open(pdf_path) as document:
        page = document.load_page(page_number - 1)
        page_dict = page.get_text("dict")

        for block_index, block in enumerate(page_dict.get("blocks", [])):
            for line_index, line in enumerate(block.get("lines", [])):
                for span_index, span in enumerate(line.get("spans", [])):
                    text = " ".join(span.get("text", "").split()).strip()

                    if not text:
                        continue

                    results.append(
                        {
                            "block_index": block_index,
                            "line_index": line_index,
                            "span_index": span_index,
                            "font": span.get("font"),
                            "size": span.get("size"),
                            "bbox": [round(v, 2) for v in span.get("bbox", [])],
                            "char_count": len(text),
                            "text_preview": text[:200],
                        }
                    )

    return results


TOC_PATTERN = re.compile(r"^(.+?)\.{3,}\s*(\d+)$")


def parse_toc_entry(text: str) -> dict | None:
    cleaned = " ".join(text.split()).strip()
    match = TOC_PATTERN.match(cleaned)

    if not match:
        return None

    return {
        "title": match.group(1).strip(),
        "page": int(match.group(2)),
    }


if __name__ == "__main__":
    manifest_path = Path("data/source_manifest.csv")
    records = load_source_manifest(manifest_path)

    print("\nBASIC PDF INSPECTION")
    for result in inspect_manifest_pdfs(manifest_path):
        print("=" * 80)
        print(f"source_id: {result['source_id']}")
        print(f"title: {result['title']}")
        print(f"file_path: {result['file_path']}")
        print(f"page_count: {result['page_count']}")

        for sample in result["samples"]:
            print("-" * 80)
            print(f"page: {sample['page']}")
            print(f"char_count: {sample['char_count']}")
            print(sample["text_preview"])

    print("\nSORTED BLOCK INSPECTION")
    for record in records:
        print("=" * 80)
        print(record.source_id)

        blocks = inspect_sorted_pdf_blocks(record, page_number=3)

        for block in blocks[:15]:
            print(block)

    print("\nCOLUMN SORTED BLOCK INSPECTION")
    for record in records:
        if record.source_id != "wada_prohibited_list_2026_ko":
            continue

        result = inspect_column_sorted_pdf_blocks(record, page_number=2)

        print("=" * 80)
        print(result["source_id"])

        print("\nLEFT COLUMN")
        for block in result["left_blocks"]:
            print(block)

        print("\nRIGHT COLUMN")
        for block in result["right_blocks"]:
            print(block)

        print("\nOTHER BLOCKS")
        for block in result["other_blocks"]:
            print(block)
        print("\nSPAN INSPECTION")
    records = load_source_manifest(Path("data/source_manifest.csv"))

    for record in records:
        if record.source_id != "wada_isti_2021_ko_en":
            continue

        spans = inspect_pdf_spans(record, page_number=2)

        print("=" * 80)
        print(record.source_id)

        for span in spans[:30]:
            print(span)