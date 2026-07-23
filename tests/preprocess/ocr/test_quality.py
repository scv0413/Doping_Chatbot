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

def test_korean_ocr_noise_tokens_require_review() -> None:
    text = (
        "선정된 At 통지를 받은 MA 일치하도록 해준 ㅅ/루채취기구 ㅅ/료재취요원 "
        "SASS AL SACL If 0/2.8/ "
    ) * 12

    report = assess_text_quality(text, expects_korean=True)

    assert report.status == PageQualityStatus.NEEDS_REVIEW
    assert report.reason == "ocr_noise_token_ratio"
    assert report.ocr_noise_ratio > 0.2
