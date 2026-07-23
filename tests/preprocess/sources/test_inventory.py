from pathlib import Path

from app.preprocess.sources.inventory import (
    build_refresh_plan,
    build_source_inventory,
    compare_source_inventories,
)


def write_manifest(path: Path, source_path: Path, status: str = "ready") -> None:
    path.write_text(
        "source_id,file_path,title,authority,year,language,document_type,layout_type,processing_status,toc_pages\n"
        f"source_1,{source_path},Source,KADA,2026,ko,rules,standard,{status},\n",
        encoding="utf-8",
    )


def test_source_inventory_captures_file_identity(tmp_path: Path) -> None:
    source_path = tmp_path / "rule.pdf"
    source_path.write_bytes(b"first-version")
    manifest_path = tmp_path / "sources.csv"
    write_manifest(manifest_path, source_path)

    inventory = build_source_inventory(manifest_path)

    assert inventory.entries[0].source_id == "source_1"
    assert inventory.entries[0].exists is True
    assert inventory.entries[0].sha256
    assert inventory.entries[0].size_bytes == len(b"first-version")


def test_inventory_comparison_detects_changed_and_missing_sources(tmp_path: Path) -> None:
    source_path = tmp_path / "rule.pdf"
    source_path.write_bytes(b"first-version")
    manifest_path = tmp_path / "sources.csv"
    write_manifest(manifest_path, source_path)
    previous = build_source_inventory(manifest_path)

    source_path.write_bytes(b"second-version")
    changed = compare_source_inventories(previous, build_source_inventory(manifest_path))
    assert changed.changed_source_ids == ["source_1"]

    source_path.unlink()
    missing = compare_source_inventories(previous, build_source_inventory(manifest_path))
    assert missing.missing_source_ids == ["source_1"]


def test_refresh_plan_requires_explicit_review_override(tmp_path: Path) -> None:
    source_path = tmp_path / "rule.pdf"
    source_path.write_bytes(b"source")
    manifest_path = tmp_path / "sources.csv"
    write_manifest(manifest_path, source_path, status="needs_review")

    plan = build_refresh_plan(build_source_inventory(manifest_path))

    assert plan.can_apply is False
    assert plan.review_required_source_ids == ["source_1"]
    assert "--include-needs-review" in plan.blocking_reason
