import argparse
import json
from pathlib import Path

from app.preprocess.ocr.quality import assess_text_quality
from app.preprocess.ocr.tesseract import run_tesseract_ocr


DEFAULT_PAGES = (4, 84, 164)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render selected ISTI Korean pages with local OCR.")
    parser.add_argument("--pdf-path", type=Path, required=True)
    parser.add_argument("--pages", type=int, nargs="+", default=DEFAULT_PAGES)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    import fitz

    with fitz.open(args.pdf_path) as document:
        for page_number in args.pages:
            text = run_tesseract_ocr(document.load_page(page_number - 1))
            report = assess_text_quality(text, expects_korean=True)
            print(
                json.dumps(
                    {
                        "page": page_number,
                        "extraction_method": "tesseract_ocr",
                        "ocr_language": "kor+eng",
                        "quality": report.model_dump(mode="json"),
                        "text": text,
                    },
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    main()
