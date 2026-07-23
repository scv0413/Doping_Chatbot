"""Create review-only ISTI English/Korean clause alignment candidates."""

import argparse
import json
from pathlib import Path

import fitz

from app.preprocess.align.isti import build_alignment_candidates
from app.preprocess.ocr.quality import assess_text_quality
from app.preprocess.ocr.tesseract import run_tesseract_ocr
from app.preprocess.pdf.loader import blocks_to_text, parse_pdf_span_lines


ISTI_SOURCE_ID = "wada_isti_2021_ko_en"


def parse_page_pairs(values: list[str]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []

    for value in values:
        try:
            english_page, korean_page = (int(part) for part in value.split(":", maxsplit=1))
        except ValueError as error:
            raise argparse.ArgumentTypeError(
                f"Invalid page pair '{value}'. Use ENGLISH_PAGE:KOREAN_PAGE, for example 83:84."
            ) from error

        if english_page < 1 or korean_page < 1:
            raise argparse.ArgumentTypeError("Page numbers must be positive integers.")

        pairs.append((english_page, korean_page))

    return pairs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create review-only English/Korean ISTI clause alignment candidates."
    )
    parser.add_argument("--pdf-path", type=Path, required=True)
    parser.add_argument(
        "--page-pairs",
        nargs="+",
        required=True,
        metavar="ENGLISH:KOREAN",
        help="Candidate page pairs, for example 83:84 163:164.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help="Optional JSONL artifact path. Omit to print candidates only.",
    )
    return parser


def collect_page_texts(
    pdf_path: Path,
    page_pairs: list[tuple[int, int]],
) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    english_pages: dict[int, str] = {}
    korean_pages: dict[int, str] = {}
    korean_quality: dict[int, str] = {}

    with fitz.open(pdf_path) as document:
        for english_page_number, korean_page_number in page_pairs:
            _validate_page_number(document, english_page_number)
            _validate_page_number(document, korean_page_number)

            english_page = document.load_page(english_page_number - 1)
            english_pages[english_page_number] = blocks_to_text(parse_pdf_span_lines(english_page))

            korean_page = document.load_page(korean_page_number - 1)
            korean_text = run_tesseract_ocr(korean_page)
            korean_pages[korean_page_number] = korean_text
            korean_quality[korean_page_number] = assess_text_quality(
                korean_text,
                expects_korean=True,
            ).status

    return english_pages, korean_pages, korean_quality


def serialize_candidate(candidate: object) -> str:
    return json.dumps(
        {
            "source_id": ISTI_SOURCE_ID,
            **candidate.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )


def write_candidates(lines: list[str], output_path: Path | None) -> None:
    if output_path is None:
        for line in lines:
            print(line)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"saved review-only candidates: {len(lines)} -> {output_path}")


def _validate_page_number(document: fitz.Document, page_number: int) -> None:
    if page_number > document.page_count:
        raise ValueError(f"Page {page_number} exceeds PDF page count {document.page_count}.")


def main() -> None:
    args = build_parser().parse_args()
    page_pairs = parse_page_pairs(args.page_pairs)
    english_pages, korean_pages, korean_quality = collect_page_texts(args.pdf_path, page_pairs)
    candidates = build_alignment_candidates(
        english_pages=english_pages,
        korean_pages=korean_pages,
        korean_quality=korean_quality,
    )
    write_candidates([serialize_candidate(candidate) for candidate in candidates], args.output_path)


if __name__ == "__main__":
    main()
