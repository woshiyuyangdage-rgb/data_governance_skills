"""Tests for local batch snapshot storage."""

from pathlib import Path

from app.core.governance import batch_snapshot_store
from app.core.models.object_fingerprint import ObjectFingerprint


def test_batch_snapshot_store_save_load_and_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(batch_snapshot_store, "SNAPSHOT_DIR", tmp_path)

    path = batch_snapshot_store.save_batch_snapshot(
        "snapshot_test",
        [
            ObjectFingerprint(
                object_type="table",
                object_name="customer",
                fingerprint="abc",
            )
        ],
        metadata={"group_by": "system_name"},
    )
    snapshots = batch_snapshot_store.list_batch_snapshots("snapshot_test")
    latest = batch_snapshot_store.load_latest_batch_snapshot("snapshot_test")

    assert Path(path).exists()
    assert len(snapshots) == 1
    assert latest is not None
    assert latest["batch_name"] == "snapshot_test"
    assert latest["fingerprints"][0].object_name == "customer"

