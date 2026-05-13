"""Tests for local governance backlog persistence."""

from pathlib import Path

from app.core.governance import backlog_store
from app.core.models.governance_backlog_item import GovernanceBacklogItem


def _patch_store_paths(tmp_path: Path, monkeypatch) -> None:
    backlog_dir = tmp_path / "governance_backlog"
    monkeypatch.setattr(backlog_store, "BACKLOG_DIR", backlog_dir)
    monkeypatch.setattr(
        backlog_store,
        "BACKLOG_ITEMS_PATH",
        backlog_dir / "backlog_items.json",
    )
    monkeypatch.setattr(
        backlog_store,
        "BACKLOG_SNAPSHOTS_DIR",
        backlog_dir / "backlog_snapshots",
    )


def _item(backlog_id: str, status: str = "proposed") -> GovernanceBacklogItem:
    return GovernanceBacklogItem(
        backlog_id=backlog_id,
        object_type="table",
        object_name="sales_order",
        gap_type="standard_mapping_gap",
        action="Review and confirm standard mappings",
        owner_role="business_data_steward",
        priority="key_tracking",
        status=status,
    )


def test_load_backlog_items_returns_empty_when_file_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_store_paths(tmp_path, monkeypatch)

    assert backlog_store.load_backlog_items() == []
    assert backlog_store.list_backlog_items() == []


def test_save_append_lookup_and_update_backlog_items(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_store_paths(tmp_path, monkeypatch)

    save_result = backlog_store.save_backlog_items([_item("backlog_a")])
    append_result = backlog_store.append_backlog_items([_item("backlog_b")])

    assert save_result["saved_count"] == 1
    assert Path(str(save_result["path"])).exists()
    assert append_result["saved_count"] == 2
    assert append_result["snapshot_path"] is not None
    assert Path(str(append_result["snapshot_path"])).exists()

    lookup = backlog_store.build_backlog_lookup()
    assert set(lookup) == {"backlog_a", "backlog_b"}
    assert backlog_store.get_backlog_item("backlog_a") is not None

    update_result = backlog_store.update_backlog_item_status(
        "backlog_a",
        "accepted",
        note="Accepted for handling.",
    )
    updated = backlog_store.get_backlog_item("backlog_a")

    assert update_result.status == "success"
    assert update_result.old_status == "proposed"
    assert update_result.new_status == "accepted"
    assert updated is not None
    assert updated.status == "accepted"
    assert updated.notes == "Accepted for handling."


def test_update_missing_backlog_item_returns_not_found(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_store_paths(tmp_path, monkeypatch)

    result = backlog_store.update_backlog_item_status("missing", "accepted")

    assert result.status == "not_found"
    assert result.old_status is None
