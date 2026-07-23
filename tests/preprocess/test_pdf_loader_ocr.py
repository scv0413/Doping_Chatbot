from pathlib import Path

import fitz

from app.preprocess.ocr.fallback import PageExtractionResult
from app.preprocess.ocr.quality import PageQualityStatus, TextQualityReport
from app.preprocess.pdf.loader import inspect_pdf_page_loading, load_pdf_pages
from app.preprocess.sources.schemas import (
    Authority,
    DocumentMetadata,
    DocumentType,
    Language,
    LayoutType,
    ProcessingStatus,
    SourceType,
)


def test_isti_even_page_preserves_ocr_text_and_provenance(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "isti.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(pdf_path)
    document.close()

    metadata = DocumentMetadata(
        source_id="wada_isti_2021_ko_en",
        source_type=SourceType.PDF,
        title="ISTI",
        authority=Authority.WADA,
        document_type=DocumentType.TESTING_STANDARD,
        layout_type=LayoutType.MIXED_LANGUAGE,
        processing_status=ProcessingStatus.NEEDS_REVIEW,
        file_path=pdf_path,
        language=Language.MIXED,
    )
    result = PageExtractionResult(
        text="복구된 한국어 본문 " * 20,
        extraction_method="tesseract_ocr",
        quality_report=TextQualityReport(
            status=PageQualityStatus.ACCEPTED,
            char_count=200,
            hangul_ratio=0.8,
            suspicious_ratio=0.0,
        ),
        ocr_language="kor+eng",
    )

    monkeypatch.setattr(
        "app.preprocess.pdf.loader.parse_pdf_span_lines",
        lambda page: [{"text": "áᔍ ၰ᳑", "x0": 0, "y0": 0, "x1": 1, "y1": 1}],
    )
    monkeypatch.setattr("app.preprocess.pdf.loader.resolve_page_text", lambda page, **kwargs: result)

    chunks = load_pdf_pages(metadata, start_page=2, end_page=2)

    assert len(chunks) == 1
    assert chunks[0].text == result.text
    assert chunks[0].metadata.page == 2
    assert chunks[0].metadata.extraction_method == "tesseract_ocr"
    assert chunks[0].metadata.quality_status == PageQualityStatus.ACCEPTED
    assert chunks[0].metadata.ocr_language == "kor+eng"

def test_isti_even_page_inspection_reports_ocr_provenance(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "isti-inspect.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(pdf_path)
    document.close()

    metadata = DocumentMetadata(
        source_id="wada_isti_2021_ko_en", source_type=SourceType.PDF, title="ISTI",
        authority=Authority.WADA, document_type=DocumentType.TESTING_STANDARD,
        layout_type=LayoutType.MIXED_LANGUAGE, processing_status=ProcessingStatus.NEEDS_REVIEW,
        file_path=pdf_path, language=Language.MIXED,
    )
    result = PageExtractionResult(
        text="복구된 한국어 본문 " * 20, extraction_method="tesseract_ocr",
        quality_report=TextQualityReport(status=PageQualityStatus.ACCEPTED, char_count=200, hangul_ratio=0.8, suspicious_ratio=0.0),
        ocr_language="kor+eng",
    )
    monkeypatch.setattr("app.preprocess.pdf.loader.parse_pdf_span_lines", lambda page: [{"text": "áᔍ ၰ᳑", "x0": 0, "y0": 0, "x1": 1, "y1": 1}])
    monkeypatch.setattr("app.preprocess.pdf.loader.resolve_page_text", lambda page, **kwargs: result)

    decision = inspect_pdf_page_loading(metadata, start_page=2, end_page=2)[0]

    assert decision["status"] == "loaded"
    assert decision["extraction_method"] == "tesseract_ocr"
    assert decision["quality_status"] == "accepted"
