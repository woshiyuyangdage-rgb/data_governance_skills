"""Tests for incremental diff service."""

from app.core.governance.incremental_diff_service import IncrementalDiffService
from app.core.models.object_fingerprint import ObjectFingerprint


def test_incremental_diff_service_detects_all_basic_categories() -> None:
    service = IncrementalDiffService()
    old = [
        ObjectFingerprint(object_type="table", object_name="unchanged", fingerprint="a"),
        ObjectFingerprint(object_type="table", object_name="changed", fingerprint="b"),
        ObjectFingerprint(object_type="table", object_name="removed", fingerprint="c"),
    ]
    new = [
        ObjectFingerprint(object_type="table", object_name="unchanged", fingerprint="a"),
        ObjectFingerprint(object_type="table", object_name="changed", fingerprint="d"),
        ObjectFingerprint(object_type="table", object_name="new", fingerprint="e"),
    ]

    diff_items = service.compare_fingerprints(old, new)
    summary = service.build_incremental_diff_summary(diff_items)
    changed_scope = service.filter_changed_objects(diff_items)

    assert {item.diff_type for item in diff_items} == {
        "new",
        "changed",
        "unchanged",
        "removed",
    }
    assert summary.new_count == 1
    assert summary.changed_count == 1
    assert summary.unchanged_count == 1
    assert summary.removed_count == 1
    assert {item.object_name for item in changed_scope} == {"new", "changed"}

