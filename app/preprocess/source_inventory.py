import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.preprocess.manifest import load_source_manifest
from app.preprocess.schemas import ProcessingStatus


class SourceInventoryEntry(BaseModel):
    source_id: str
    file_path: str
    processing_status: ProcessingStatus
    exists: bool
    size_bytes: int | None = None
    sha256: str | None = None


class SourceInventory(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    manifest_path: str
    entries: list[SourceInventoryEntry]


class SourceInventoryComparison(BaseModel):
    added_source_ids: list[str] = Field(default_factory=list)
    changed_source_ids: list[str] = Field(default_factory=list)
    missing_source_ids: list[str] = Field(default_factory=list)
    unchanged_source_ids: list[str] = Field(default_factory=list)


class DataRefreshPlan(BaseModel):
    can_apply: bool
    blocking_reason: str | None = None
    review_required_source_ids: list[str] = Field(default_factory=list)
    missing_source_ids: list[str] = Field(default_factory=list)


def build_source_inventory(manifest_path: Path) -> SourceInventory:
    entries: list[SourceInventoryEntry] = []
    for source in load_source_manifest(manifest_path):
        if source.file_path is None:
            continue
        file_path = source.file_path
        exists = file_path.is_file()
        entries.append(
            SourceInventoryEntry(
                source_id=source.source_id,
                file_path=str(file_path),
                processing_status=source.processing_status,
                exists=exists,
                size_bytes=file_path.stat().st_size if exists else None,
                sha256=calculate_file_sha256(file_path) if exists else None,
            )
        )

    return SourceInventory(manifest_path=str(manifest_path), entries=entries)


def calculate_file_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_source_inventory(inventory_path: Path, inventory: SourceInventory) -> None:
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(inventory.model_dump_json(indent=2), encoding="utf-8")


def load_source_inventory(inventory_path: Path) -> SourceInventory:
    return SourceInventory.model_validate_json(inventory_path.read_text(encoding="utf-8"))


def compare_source_inventories(
    previous: SourceInventory,
    current: SourceInventory,
) -> SourceInventoryComparison:
    previous_by_id = {entry.source_id: entry for entry in previous.entries}
    current_by_id = {entry.source_id: entry for entry in current.entries}
    comparison = SourceInventoryComparison()

    for source_id, entry in current_by_id.items():
        previous_entry = previous_by_id.get(source_id)
        if previous_entry is None:
            comparison.added_source_ids.append(source_id)
        elif not entry.exists:
            comparison.missing_source_ids.append(source_id)
        elif (
            previous_entry.sha256 != entry.sha256
            or previous_entry.file_path != entry.file_path
            or previous_entry.processing_status != entry.processing_status
        ):
            comparison.changed_source_ids.append(source_id)
        else:
            comparison.unchanged_source_ids.append(source_id)

    for source_id in previous_by_id:
        if source_id not in current_by_id:
            comparison.missing_source_ids.append(source_id)

    comparison.missing_source_ids = sorted(set(comparison.missing_source_ids))
    for field_name in ("added_source_ids", "changed_source_ids", "unchanged_source_ids"):
        setattr(comparison, field_name, sorted(getattr(comparison, field_name)))
    return comparison


def build_refresh_plan(
    inventory: SourceInventory,
    include_needs_review: bool = False,
) -> DataRefreshPlan:
    missing_source_ids = sorted(entry.source_id for entry in inventory.entries if not entry.exists)
    review_required_source_ids = sorted(
        entry.source_id
        for entry in inventory.entries
        if entry.processing_status == ProcessingStatus.NEEDS_REVIEW
    )

    if missing_source_ids:
        return DataRefreshPlan(
            can_apply=False,
            blocking_reason="Missing source files must be restored before refresh.",
            missing_source_ids=missing_source_ids,
            review_required_source_ids=review_required_source_ids,
        )

    if review_required_source_ids and not include_needs_review:
        return DataRefreshPlan(
            can_apply=False,
            blocking_reason=(
                "Sources marked needs_review require --include-needs-review before refresh."
            ),
            review_required_source_ids=review_required_source_ids,
        )

    return DataRefreshPlan(
        can_apply=True,
        review_required_source_ids=review_required_source_ids,
    )


def format_refresh_report(
    inventory: SourceInventory,
    comparison: SourceInventoryComparison | None,
    plan: DataRefreshPlan,
) -> str:
    payload = {
        "inventory": inventory.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json") if comparison else None,
        "plan": plan.model_dump(mode="json"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
