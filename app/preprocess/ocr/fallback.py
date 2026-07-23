from typing import Any

from pydantic import BaseModel

from app.preprocess.ocr.quality import (
    PageQualityStatus,
    TextQualityReport,
    assess_text_quality,
)
from app.preprocess.ocr.tesseract import DEFAULT_OCR_LANGUAGE, TesseractError, run_tesseract_ocr


class PageExtractionResult(BaseModel):
    text: str | None
    extraction_method: str
    quality_report: TextQualityReport
    ocr_language: str | None = None


def resolve_page_text(
    page: Any,
    *,
    text_layer_text: str,
    expects_korean: bool,
) -> PageExtractionResult:
    text_report = assess_text_quality(text_layer_text, expects_korean=expects_korean)
    if text_report.status == PageQualityStatus.ACCEPTED or not expects_korean:
        return PageExtractionResult(
            text=text_layer_text,
            extraction_method="text_layer",
            quality_report=text_report,
        )

    try:
        ocr_text = run_tesseract_ocr(page, language=DEFAULT_OCR_LANGUAGE)
    except TesseractError as error:
        return PageExtractionResult(
            text=None,
            extraction_method="tesseract_ocr",
            quality_report=text_report.model_copy(update={"reason": f"ocr_unavailable:{error}"}),
            ocr_language=DEFAULT_OCR_LANGUAGE,
        )

    ocr_report = assess_text_quality(ocr_text, expects_korean=True)
    if ocr_report.status != PageQualityStatus.ACCEPTED:
        return PageExtractionResult(
            text=None,
            extraction_method="tesseract_ocr",
            quality_report=ocr_report.model_copy(update={"reason": f"ocr_{ocr_report.reason}"}),
            ocr_language=DEFAULT_OCR_LANGUAGE,
        )

    return PageExtractionResult(
        text=ocr_text,
        extraction_method="tesseract_ocr",
        quality_report=ocr_report,
        ocr_language=DEFAULT_OCR_LANGUAGE,
    )
