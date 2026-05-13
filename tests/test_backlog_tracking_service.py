"""Tests for governance backlog tracking service."""

from pathlib import Path

from app.core.governance import backlog_store
from app.core.governance.backlog_tracking_service import GovernanceBacklogTrackingService
from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction


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


def _service() -> GovernanceBacklogTrackingService:
    return GovernanceBacklogTrackingService(
        policies={
            "backlog_policy": {
                "default_status": "proposed",
                "include_dependency_notes": True,
                "include_owner_hints": True,
                "include_completion_criteria": True,
            },
            "status_transition_policy": {
                "allowed_transitions": {
                    "proposed": ["accepted", "dropped"],
                    "accepted": ["in_progress", "blocked", "dropped"],
                    "in_progress": ["blocked", "completed"],
                    "blocked": ["in_progress", "dropped"],
                    "completed": [],
                    "dropped": [],
                }
            },
            "priority_mapping": {
                "key_tracking": {"urgency_score": 2},
            },
            "owner_role_defaults": {
                "standard_mapping_gap": "business_data_steward",
            },
        },
        status_templates={
            "statuses": {
                "proposed": {"description": "Suggested"},
                "accepted": {"description": "Accepted"},
                "in_progress": {"description": "In progress"},
                "blocked": {"description": "Blocked"},
                "completed": {"description": "Completed"},
                "dropped": {"description": "Dropped"},
            }
        },
    )


def _work_package() -> GovernanceWorkPackage:
    action = RemediationAction(
        object_type="table",
        object_name="sales_order",
        gap_type="standard_mapping_gap",
        action="Review and confirm standard mappings",
        owner_role="business_data_steward",
        priority="key_tracking",
    )
    gap = GovernanceGap(
        object_type="table",
        object_name="sales_order",
        gap_type="standard_mapping_gap",
        category="mapping",
        severity="medium",
        source_signals=["standard_mapping_low_confidence"],
    )
    score = ReadinessScore(
        object_type="table",
        object_name="sales_order",
        overall_score=0.66,
        readiness_level="partially_ready",
    )
    return GovernanceWorkPackage(
        package_name="tracking_test",
        readiness_scores=[score],
        governance_gaps=[gap],
        remediation_actions=[action],
    )


def test_build_persist_update_and_summarize_backlog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_store_paths(tmp_path, monkeypatch)
    service = _service()

    items, summary = service.build_backlog_from_work_package(_work_package())
    persist_result = service.persist_backlog_items(items)
    update_result = service.update_backlog_status(
        items[0].backlog_id,
        "accepted",
        note="Accepted by governance lead.",
    )
    persisted_summary = service.summarize_backlog()

    assert len(items) == 1
    assert summary.total_items == 1
    assert persist_result["saved_count"] == 1
    assert update_result.status == "success"
    assert update_result.old_status == "proposed"
    assert update_result.new_status == "accepted"
    assert persisted_summary.by_status == {"accepted": 1}


def test_status_transition_validation_rejects_invalid_transition(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_store_paths(tmp_path, monkeypatch)
    service = _service()
    items, _ = service.build_backlog_from_work_package(_work_package())
    service.persist_backlog_items(items)

    result = service.update_backlog_status(items[0].backlog_id, "completed")

    assert result.status == "invalid_transition"
    assert result.old_status == "proposed"
    assert result.new_status == "completed"


def test_filter_backlog_items_supports_dashboard_fields() -> None:
    service = _service()
    items, _ = service.build_backlog_from_work_package(_work_package())

    assert service.filter_backlog_items(items, status="proposed") == items
    assert service.filter_backlog_items(items, priority="key_tracking") == items
    assert service.filter_backlog_items(items, owner_role="business_data_steward") == items
    assert service.filter_backlog_items(items, gap_type="standard_mapping_gap") == items
    assert service.filter_backlog_items(items, status="completed") == []
