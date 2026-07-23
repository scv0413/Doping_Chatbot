import pytest

from app.preprocess.ocr.fallback import resolve_page_text


def test_accepted_text_layer_does_not_call_ocr(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.preprocess.ocr.fallback.run_tesseract_ocr",
        lambda *args, **kwargs: pytest.fail("OCR must not run"),
    )

    result = resolve_page_text(
        object(),
        text_layer_text="도핑검사는 규정에 따라 실시됩니다. " * 20,
        expects_korean=True,
    )

    assert result.extraction_method == "text_layer"
    assert result.ocr_language is None


def test_low_quality_korean_uses_ocr(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.preprocess.ocr.fallback.run_tesseract_ocr",
        lambda *args, **kwargs: "도핑검사는 규정에 따라 실시됩니다. " * 20,
    )

    result = resolve_page_text(
        object(),
        text_layer_text="áᔍ ၰ᳑ ᔍǎᱽ⢽ᵡ " * 20,
        expects_korean=True,
    )

    assert result.text is not None
    assert result.extraction_method == "tesseract_ocr"
    assert result.ocr_language == "kor+eng"
    assert result.quality_report.status.value == "accepted"
