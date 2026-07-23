"""Render a non-indexable human-review draft from ISTI alignment candidates."""

import argparse
import json
from pathlib import Path

from app.preprocess.align.isti import IstiSectionAlignmentCandidate
from app.preprocess.align.manual_review import render_manual_review_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a non-indexable ISTI Korean human-review draft."
    )
    parser.add_argument("--candidates-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    return parser


def load_candidates(path: Path) -> list[IstiSectionAlignmentCandidate]:
    candidates: list[IstiSectionAlignmentCandidate] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            candidates.append(IstiSectionAlignmentCandidate.model_validate(json.loads(line)))

    return candidates


def main() -> None:
    args = build_parser().parse_args()
    template = render_manual_review_template(load_candidates(args.candidates_path))
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(template, encoding="utf-8")
    print(f"saved non-indexable review draft -> {args.output_path}")


if __name__ == "__main__":
    main()
