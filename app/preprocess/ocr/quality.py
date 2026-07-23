from enum import StrEnum

from pydantic import BaseModel


MIN_TEXT_CHARACTERS = 20
MIN_HANGUL_RATIO = 0.1
MAX_SUSPICIOUS_RATIO = 0.1


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


def _is_hangul(character: str) -> bool:
    return "\uac00" <= character <= "\ud7a3"


def _is_suspicious(character: str) -> bool:
    return not character.isascii() and not _is_hangul(character)


def assess_text_quality(text: str, *, expects_korean: bool) -> TextQualityReport:
    cleaned = "".join(text.split())
    char_count = len(cleaned)

    if not cleaned:
        return TextQualityReport(
            status=PageQualityStatus.REJECTED,
            reason="empty_text",
            char_count=0,
            hangul_ratio=0.0,
            suspicious_ratio=0.0,
        )

    hangul_ratio = sum(_is_hangul(character) for character in cleaned) / char_count
    suspicious_ratio = sum(_is_suspicious(character) for character in cleaned) / char_count

    if char_count < MIN_TEXT_CHARACTERS:
        status = PageQualityStatus.NEEDS_REVIEW
        reason = "insufficient_text"
    elif expects_korean and suspicious_ratio > MAX_SUSPICIOUS_RATIO:
        status = PageQualityStatus.NEEDS_REVIEW
        reason = "suspicious_character_ratio"
    elif expects_korean and hangul_ratio < MIN_HANGUL_RATIO:
        status = PageQualityStatus.NEEDS_REVIEW
        reason = "insufficient_hangul_ratio"
    else:
        status = PageQualityStatus.ACCEPTED
        reason = None

    return TextQualityReport(
        status=status,
        reason=reason,
        char_count=char_count,
        hangul_ratio=hangul_ratio,
        suspicious_ratio=suspicious_ratio,
    )
