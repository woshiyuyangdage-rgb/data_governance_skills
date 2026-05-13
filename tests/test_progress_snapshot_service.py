"""Tests for governance progress snapshot service."""

from pathlib import Path

from app.core.governance import progress_snapshot_service
from app.core.governance.progress_snapshot_service import ProgressSnapshotService
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.readiness_score import ReadinessScore


def _item(backlog_id: str, status: str) -> GovernanceBacklogItem:
    return GovernanceBacklogItem(
        backlog_id=backlog_id,
        object_type="table",
        object_name=backlog_id,
        gap_type="standard_mapping_gap",
        action="Review governance item",
        owner_role="business_data_steward",
        priority="key_tracking",
        status=status,
    )


def test_progress_snapshot_build_save_and_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        progress_snapshot_service,
        "PROGRESS_SNAPSHOT_DIR",
        tmp_path / "progress_snapshots",
    )
    service = ProgressSnapshotService()
    items = [_item("backlog_1", "completed"), _item("backlog_2", "blocked")]
    sla_statuses = [
        BacklogSlaStatus(backlog_id="backlog_1", is_overdue=False),
        BacklogSlaStatus(backlog_id="backlog_2", is_overdue=True),
    ]
    readiness_scores = [
        ReadinessScore(
            object_type="table",
            object_name="sales_order",
            overall_score=0.8,
            readiness_level="ready",
        )
    ]

    snapshot = service.build_progress_snapshot(
        items,
        backlog_sla_statuses=sla_statuses,
        readiness_scores=readiness_scores,
        notes="snapshot test",
    )
    save_result = service.save_progress_snapshot(snapshot)
    snapshots = service.list_progress_snapshots()

    assert snapshot.snapshot_id.startswith("snapshot_")
    assert snapshot.total_backlog_items == 2
    assert snapshot.completed_count == 1
    assert snapshot.blocked_count == 1
    assert snapshot.overdue_count == 1
    assert snapshot.avg_readiness_score == 0.8
    assert Path(str(save_result["path"])).exists()
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_id == snapshot.snapshot_id
