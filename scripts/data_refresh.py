import argparse
from pathlib import Path

from app.chat.retrieval.indexer import index_chunks
from app.preprocess.transform.chunker import chunk_pages
from app.preprocess.transform.preprocess import preprocess_manifest
from app.preprocess.sources.inventory import (
    build_refresh_plan,
    build_source_inventory,
    compare_source_inventories,
    format_refresh_report,
    load_source_inventory,
    write_source_inventory,
)

DEFAULT_MANIFEST_PATH = Path("data/source_manifest.csv")
DEFAULT_INVENTORY_PATH = Path("data/operations/source-inventory.json")


def run_data_refresh(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    inventory_path: Path = DEFAULT_INVENTORY_PATH,
    apply: bool = False,
    include_needs_review: bool = False,
) -> int:
    current_inventory = build_source_inventory(manifest_path)
    previous_inventory = load_source_inventory(inventory_path) if inventory_path.exists() else None
    comparison = (
        compare_source_inventories(previous_inventory, current_inventory)
        if previous_inventory
        else None
    )
    plan = build_refresh_plan(current_inventory, include_needs_review=include_needs_review)
    print(format_refresh_report(current_inventory, comparison, plan))

    if not apply:
        return 0
    if not plan.can_apply:
        return 2

    preprocess_manifest(manifest_path=manifest_path)
    chunk_pages()
    index_chunks()
    write_source_inventory(inventory_path, current_inventory)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit source changes and optionally rebuild the RAG index."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include-needs-review", action="store_true")
    args = parser.parse_args()

    raise SystemExit(
        run_data_refresh(
            manifest_path=args.manifest,
            inventory_path=args.inventory,
            apply=args.apply,
            include_needs_review=args.include_needs_review,
        )
    )


if __name__ == "__main__":
    main()
