from app.preprocess.ocr.quality import PageQualityStatus, assess_text_quality


def test_korean_mojibake_requires_review() -> None:
    report = assess_text_quality("áᔍ ၰ᳑ ᔍǎᱽ⢽ᵡ " * 20, expects_korean=True)

    assert report.status == PageQualityStatus.NEEDS_REVIEW
    assert report.reason == "suspicious_character_ratio"


def test_readable_korean_is_accepted() -> None:
    report = assess_text_quality("도핑검사는 규정에 따라 실시됩니다. " * 20, expects_korean=True)

    assert report.status == PageQualityStatus.ACCEPTED
    assert report.hangul_ratio > 0.5


def test_empty_text_is_rejected() -> None:
    report = assess_text_quality("   ", expects_korean=True)

    assert report.status == PageQualityStatus.REJECTED
    assert report.reason == "empty_text"
