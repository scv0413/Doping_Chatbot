from app.preprocess.align.isti import IstiSectionAlignmentCandidate
from app.preprocess.align.manual_review import render_manual_review_template


def test_renders_review_only_template_from_section_candidates() -> None:
    template = render_manual_review_template(
        [
            IstiSectionAlignmentCandidate(
                english_page=83,
                korean_page=84,
                section_numbers=["5.3.5"],
                korean_quality_status="needs_review",
            )
        ]
    )

    assert "<!-- review-status: draft -->" in template
    assert "## 5.3.5" in template
    assert "- English source page: 83" in template
    assert "- Korean OCR page: 84" in template
    assert "- Korean OCR quality: needs_review" in template
    assert "<!-- Human reviewer: write verified Korean text here. -->" in template
    assert "processing_status: ready" not in template
