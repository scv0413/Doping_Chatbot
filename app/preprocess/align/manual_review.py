"""Create draft handoff documents for human review of ISTI Korean clauses."""

from app.preprocess.align.isti import IstiSectionAlignmentCandidate


def render_manual_review_template(
    candidates: list[IstiSectionAlignmentCandidate],
) -> str:
    """Render a non-indexable draft for a human Korean-language reviewer."""

    lines = [
        "# ISTI Korean Manual Review Draft",
        "",
        "<!-- review-status: draft -->",
        "<!-- This document is not a retrieval source and must not be indexed. -->",
        "",
        "This draft identifies clause locations only. Review the official English page and",
        "the Korean PDF page, then write a verified Korean manual source separately.",
    ]

    for candidate in candidates:
        for section_number in candidate.section_numbers:
            lines.extend(
                [
                    "",
                    f"## {section_number}",
                    "",
                    f"- English source page: {candidate.english_page}",
                    f"- Korean OCR page: {candidate.korean_page}",
                    f"- Korean OCR quality: {candidate.korean_quality_status}",
                    "- Alignment use: reviewer navigation only",
                    "",
                    "<!-- Human reviewer: write verified Korean text here. -->",
                ]
            )

    return "\n".join(lines) + "\n"
