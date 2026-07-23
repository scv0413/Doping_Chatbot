"""Build conservative, review-only section alignment candidates for WADA ISTI."""

import re
from collections import defaultdict

from pydantic import BaseModel, Field


SECTION_NUMBER_PATTERN = re.compile(r"(?<![\d.])(\d+(?:\.\d+)+)(?![\d.])")


class IstiSectionAlignmentCandidate(BaseModel):
    """A unique English/Korean clause-number match for human review only."""

    english_page: int
    korean_page: int
    section_numbers: list[str] = Field(min_length=1)
    korean_quality_status: str
    review_only: bool = True
    usable_for_retrieval: bool = False


def extract_section_numbers(text: str) -> set[str]:
    """Extract hierarchical clause numbers such as ``5.3.5`` and ``13.1``."""

    return set(SECTION_NUMBER_PATTERN.findall(text))


def build_alignment_candidates(
    *,
    english_pages: dict[int, str],
    korean_pages: dict[int, str],
    korean_quality: dict[int, str],
) -> list[IstiSectionAlignmentCandidate]:
    """Return only clause matches that occur on one page in each language.

    Korean OCR is intentionally never promoted to retrieval evidence here. The
    resulting candidates help a reviewer locate the matching English source
    when creating a separately verified manual Korean source.
    """

    english_sections = _index_pages_by_section(english_pages)
    korean_sections = _index_pages_by_section(korean_pages)
    matches_by_page_pair: dict[tuple[int, int], list[str]] = defaultdict(list)

    for section_number in sorted(english_sections.keys() & korean_sections.keys()):
        english_page_numbers = english_sections[section_number]
        korean_page_numbers = korean_sections[section_number]

        if len(english_page_numbers) != 1 or len(korean_page_numbers) != 1:
            continue

        page_pair = (next(iter(english_page_numbers)), next(iter(korean_page_numbers)))
        matches_by_page_pair[page_pair].append(section_number)

    return [
        IstiSectionAlignmentCandidate(
            english_page=english_page,
            korean_page=korean_page,
            section_numbers=sorted(section_numbers, key=_section_number_sort_key),
            korean_quality_status=korean_quality.get(korean_page, "unknown"),
        )
        for (english_page, korean_page), section_numbers in sorted(matches_by_page_pair.items())
    ]


def _index_pages_by_section(pages: dict[int, str]) -> dict[str, set[int]]:
    index: dict[str, set[int]] = defaultdict(set)

    for page_number, text in pages.items():
        for section_number in extract_section_numbers(text):
            index[section_number].add(page_number)

    return index


def _section_number_sort_key(section_number: str) -> tuple[int, ...]:
    return tuple(int(part) for part in section_number.split("."))
