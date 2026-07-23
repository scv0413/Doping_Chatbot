import pytest

from app.preprocess.ocr.tesseract import TesseractUnavailableError, ensure_tesseract_available


def test_ensure_tesseract_available_explains_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr("app.preprocess.ocr.tesseract.shutil.which", lambda _: None)

    with pytest.raises(TesseractUnavailableError, match="tesseract executable"):
        ensure_tesseract_available(language="kor+eng")
