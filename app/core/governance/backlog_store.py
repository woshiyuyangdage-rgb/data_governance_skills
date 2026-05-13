"""Local JSON store for governance backlog tracking."""

from datetime import datetime
import json
from pathlib import Path

from app.core.models.backlog_update_result import BacklogUpdateResult
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKLOG_DIR = PROJECT_ROOT / "app" / "data" / "governance_backlog"
BACKLOG_ITEMS_PATH = BACKLOG_DIR / "backlog_items.json"
BACKLOG_SNAPSHOTS_DIR = BACKLOG_DIR / "backlog_snapshots"


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _snapshot_existing_file() -> str | None:
    if not BACKLOG_ITEMS_PATH.exists():
        return None
    ensure_directory(BACKLOG_SNAPSHOTS_DIR)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_path = BACKLOG_SNAPSHOTS_DIR / f"{timestamp}_backlog_items.json"
    snapshot_path.write_text(
        BACKLOG_ITEMS_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return str(snapshot_path)


def load_backlog_items() -> list[GovernanceBacklogItem]:
    """Load backlog items from local JSON storage."""
    if not BACKLOG_ITEMS_PATH.exists():
        return []
    try:
        payload = json.loads(BACKLOG_ITEMS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    records = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return []
    return [
        item
        if isinstance(item, GovernanceBacklogItem)
        else GovernanceBacklogItem.model_validate(item)
        for item in records
    ]


def save_backlog_items(items: list[GovernanceBacklogItem]) -> dict[str, object]:
    """Save backlog items and create a snapshot of the previous file when present."""
    ensure_directory(BACKLOG_DIR)
    snapshot_path = _snapshot_existing_file()
    BACKLOG_ITEMS_PATH.write_text(
        json.dumps(
            {"items": [item.model_dump() for item in items]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "saved_count": len(items),
        "path": str(BACKLOG_ITEMS_PATH),
        "snapshot_path": snapshot_path,
    }


def build_backlog_lookup(
    items: list[GovernanceBacklogItem] | None = None,
) -> dict[str, GovernanceBacklogItem]:
    """Build a lookup by backlog id."""
    resolved_items = load_backlog_items() if items is None else items
    return {item.backlog_id: item for item in resolved_items}


def append_backlog_items(items: list[GovernanceBacklogItem]) -> dict[str, object]:
    """Append or replace backlog items by deterministic backlog id."""
    lookup = build_backlog_lookup()
    for item in items:
        existing = lookup.get(item.backlog_id)
        if existing is not None:
            item.status = existing.status
            item.created_at = existing.created_at or item.created_at
            item.notes = existing.notes or item.notes
        item.updated_at = _utc_now()
        lookup[item.backlog_id] = item
    return save_backlog_items(list(lookup.values()))


def get_backlog_item(backlog_id: str) -> GovernanceBacklogItem | None:
    """Return one backlog item by id."""
    return build_backlog_lookup().get(backlog_id)


def list_backlog_items() -> list[GovernanceBacklogItem]:
    """Return all local backlog items."""
    return load_backlog_items()


def update_backlog_item_status(
    backlog_id: str,
    new_status: str,
    note: str | None = None,
) -> BacklogUpdateResult:
    """Update one backlog status without transition validation."""
    items = load_backlog_items()
    updated_at = _utc_now()
    for item in items:
        if item.backlog_id != backlog_id:
            continue
        old_status = item.status
        item.status = new_status
        item.updated_at = updated_at
        if note:
            item.notes = note if not item.notes else f"{item.notes}\n{note}"
        save_backlog_items(items)
        return BacklogUpdateResult(
            backlog_id=backlog_id,
            old_status=old_status,
            new_status=new_status,
            status="success",
            message=f"Backlog item '{backlog_id}' status updated.",
            updated_at=updated_at,
        )
    return BacklogUpdateResult(
        backlog_id=backlog_id,
        old_status=None,
        new_status=None,
        status="not_found",
        message=f"Backlog item '{backlog_id}' was not found.",
        updated_at=updated_at,
    )


# TODO: replace JSON storage with project-management adapter exports after local tracking stabilizes.

