"""Build indexable chunks from an already approved human-review manual."""

import argparse
from pathlib import Path

from app.preprocess.manual_loader import build_approved_manual_chunks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build chunks only from an approved, human-reviewed Korean manual."
    )
    parser.add_argument("--manual-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    build_approved_manual_chunks(args.manual_path, args.output_path)


if __name__ == "__main__":
    main()
