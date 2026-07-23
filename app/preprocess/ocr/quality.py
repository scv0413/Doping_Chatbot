import re
from enum import StrEnum

from pydantic import BaseModel


MIN_TEXT_CHARACTERS = 20
MIN_HANGUL_RATIO = 0.1
MAX_SUSPICIOUS_RATIO = 0.1
MAX_OCR_NOISE_TOKEN_RATIO = 0.1
KNOWN_ASCII_TOKENS = {"WADA", "ISTI", "TUE"}


class PageQualityStatus(StrEnum):
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class TextQualityReport(BaseModel):
    status: PageQualityStatus
    reason: str | None = None
    char_count: int
    hangul_ratio: float
    suspicious_ratio: float
    ocr_noise_ratio: float = 0.0


def _is_hangul(character: str) -> bool:
    return "\uac00" <= character <= "\ud7a3"


def _is_suspicious(character: str) -> bool:
    return not character.isascii() and not _is_hangul(character)


def _is_ocr_noise_token(token: str) -> bool:
    normalized = token.strip(".,;:()[]{}")
    if "/" in normalized:
        return True
    ascii_letters = sum(character.isascii() and character.isalpha() for character in normalized)
    return ascii_letters >= 2 and normalized.upper() not in KNOWN_ASCII_TOKENS


def assess_text_quality(text: str, *, expects_korean: bool) -> TextQualityReport:
    cleaned = "".join(text.split())
    char_count = len(cleaned)
    if not cleaned:
        return TextQualityReport(status=PageQualityStatus.REJECTED, reason="empty_text", char_count=0, hangul_ratio=0.0, suspicious_ratio=0.0, ocr_noise_ratio=0.0)

    hangul_ratio = sum(_is_hangul(char) for char in cleaned) / char_count
    suspicious_ratio = sum(_is_suspicious(char) for char in cleaned) / char_count
    tokens = re.findall(r"[^\s]+", text)
    ocr_noise_ratio = sum(_is_ocr_noise_token(token) for token in tokens) / len(tokens)

    if char_count < MIN_TEXT_CHARACTERS:
        status, reason = PageQualityStatus.NEEDS_REVIEW, "insufficient_text"
    elif expects_korean and suspicious_ratio > MAX_SUSPICIOUS_RATIO:
        status, reason = PageQualityStatus.NEEDS_REVIEW, "suspicious_character_ratio"
    elif expects_korean and ocr_noise_ratio > MAX_OCR_NOISE_TOKEN_RATIO:
        status, reason = PageQualityStatus.NEEDS_REVIEW, "ocr_noise_token_ratio"
    elif expects_korean and hangul_ratio < MIN_HANGUL_RATIO:
        status, reason = PageQualityStatus.NEEDS_REVIEW, "insufficient_hangul_ratio"
    else:
        status, reason = PageQualityStatus.ACCEPTED, None

    return TextQualityReport(status=status, reason=reason, char_count=char_count, hangul_ratio=hangul_ratio, suspicious_ratio=suspicious_ratio, ocr_noise_ratio=ocr_noise_ratio)
