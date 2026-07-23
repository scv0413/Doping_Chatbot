"""Download an official PDF candidate only when it passes PDF integrity checks."""

import argparse
from pathlib import Path

from app.preprocess.sources.acquisition import PdfAcquisitionError, download_official_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely acquire an official WADA/KADA PDF.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        download_official_pdf(args.url, args.output_path)
    except PdfAcquisitionError as error:
        raise SystemExit(f"official PDF acquisition failed: {error}") from error

    print(f"saved verified PDF candidate -> {args.output_path}")


if __name__ == "__main__":
    main()
