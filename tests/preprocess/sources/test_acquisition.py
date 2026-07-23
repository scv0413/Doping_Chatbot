from pathlib import Path

import pytest

from app.preprocess.sources.acquisition import PdfAcquisitionError, validate_downloaded_pdf


def test_validate_downloaded_pdf_accepts_nonempty_pdf_signature(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n" + (b"x" * 2048))

    validate_downloaded_pdf(pdf_path)


def test_validate_downloaded_pdf_rejects_empty_or_non_pdf_file(tmp_path: Path) -> None:
    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(b"")

    with pytest.raises(PdfAcquisitionError, match="empty"):
        validate_downloaded_pdf(empty_path)

    html_path = tmp_path / "challenge.pdf"
    html_path.write_text("<html>challenge</html>" * 100, encoding="utf-8")

    with pytest.raises(PdfAcquisitionError, match="PDF"):
        validate_downloaded_pdf(html_path)


def test_validate_downloaded_pdf_rejects_untrusted_source_url() -> None:
    from app.preprocess.sources.acquisition import validate_source_url

    with pytest.raises(PdfAcquisitionError, match="allowed host"):
        validate_source_url("https://example.com/source.pdf", allowed_hosts=("wada-ama.org",))
