import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.chat.config import settings


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            records.append(json.loads(line))

    return records


def summarize_pages(records: list[dict[str, Any]]) -> None:
    source_counts = Counter(
        record["metadata"]["source_id"]
        for record in records
    )

    print("PAGE COUNTS BY SOURCE")
    print("=" * 80)

    for source_id, count in source_counts.items():
        print(f"{source_id}: {count}")


def summarize_skipped(records: list[dict[str, Any]]) -> None:
    reason_counts = Counter(
        record["reason"]
        for record in records
    )

    source_counts = Counter(
        record["source_id"]
        for record in records
    )

    print("\nSKIPPED COUNTS BY REASON")
    print("=" * 80)

    for reason, count in reason_counts.items():
        print(f"{reason}: {count}")

    print("\nSKIPPED COUNTS BY SOURCE")
    print("=" * 80)

    for source_id, count in source_counts.items():
        print(f"{source_id}: {count}")


def print_page_sample(
    records: list[dict[str, Any]],
    source_id: str,
    page: int | None = None,
    limit: int = 2,
) -> None:
    matched = [
        record
        for record in records
        if record["metadata"]["source_id"] == source_id
        and (page is None or record["metadata"]["page"] == page)
    ]

    print("\nPAGE SAMPLE")
    print("=" * 80)
    print(f"source_id: {source_id}")
    print(f"page: {page}")
    print(f"matched: {len(matched)}")

    for record in matched[:limit]:
        metadata = record["metadata"]

        print("-" * 80)
        print(f"page: {metadata['page']}")
        print(f"title: {metadata['title']}")
        print(record["text"][:1200])


def print_skipped_sample(
    records: list[dict[str, Any]],
    source_id: str | None = None,
    reason: str | None = None,
    limit: int = 10,
) -> None:
    matched = [
        record
        for record in records
        if (source_id is None or record["source_id"] == source_id)
        and (reason is None or record["reason"] == reason)
    ]

    print("\nSKIPPED SAMPLE")
    print("=" * 80)
    print(f"source_id: {source_id}")
    print(f"reason: {reason}")
    print(f"matched: {len(matched)}")

    for record in matched[:limit]:
        print(record)
def summarize_skipped_by_source_and_reason(records: list[dict[str, Any]]) -> None:
    counter = Counter(
        (record["source_id"], record["reason"])
        for record in records
    )

    print("\nSKIPPED COUNTS BY SOURCE AND REASON")
    print("=" * 80)

    for (source_id, reason), count in counter.items():
        print(f"{source_id} | {reason}: {count}")


def summarize_skipped_page_numbers(
    records: list[dict[str, Any]],
    source_id: str,
) -> None:
    matched = [
        record
        for record in records
        if record["source_id"] == source_id
    ]

    pages = sorted(record["page"] for record in matched)
    odd_pages = [page for page in pages if page % 2 == 1]
    even_pages = [page for page in pages if page % 2 == 0]

    print("\nSKIPPED PAGE NUMBERS")
    print("=" * 80)
    print(f"source_id: {source_id}")
    print(f"total: {len(pages)}")
    print(f"odd pages: {len(odd_pages)}")
    print(f"even pages: {len(even_pages)}")
    print(f"pages: {pages[:120]}")


if __name__ == "__main__":

    pages_path = settings.processed_data_dir / "pages.jsonl"
    skipped_path = settings.processed_data_dir / "skipped_pages.jsonl"

    pages = read_jsonl(pages_path)
    skipped = read_jsonl(skipped_path)

    summarize_pages(pages)
    summarize_skipped(skipped)

    print_page_sample(
        pages,
        source_id="kada_anti_doping_rules_2021_ko",
        limit=2,
    )

    print_page_sample(
        pages,
        source_id="wada_prohibited_list_2026_ko",
        page=5,
        limit=1,
    )

    print_skipped_sample(
        skipped,
        source_id="wada_isti_2021_ko_en",
        limit=10,
    )
    summarize_skipped_by_source_and_reason(skipped)

    summarize_skipped_page_numbers(
        skipped,
        source_id="wada_isti_2021_ko_en",
    )