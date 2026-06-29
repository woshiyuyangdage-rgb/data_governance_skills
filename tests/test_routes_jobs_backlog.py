"""Backlog, portfolio, and progress route tests."""

from pathlib import Path

from app.api.routes_jobs import (
    GovernanceBacklogBuildRequest,
    GovernanceBacklogStatusUpdateRequest,
    GovernancePortfolioAssessmentRequest,
    ProgressSnapshotRequest,
    assess_governance_portfolio_route,
    build_governance_backlog_route,
    generate_progress_snapshot_route,
    governance_backlog_route,
    governance_backlog_summary_route,
    governance_portfolio_summary_route,
    governance_progress_snapshots_route,
    update_governance_backlog_status_route,
)
from app.core.audit import trace_store
from app.core.governance import backlog_store, progress_snapshot_service


def test_governance_backlog_routes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
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

    build_response = build_governance_backlog_route(
        GovernanceBacklogBuildRequest(
            remediation_actions=[
                {
                    "object_type": "table",
                    "object_name": "sales_order",
                    "gap_type": "standard_mapping_gap",
                    "action": "Review and confirm standard mappings",
                    "owner_role": "business_data_steward",
                    "priority": "key_tracking",
                }
            ],
            persist=True,
        )
    )
    backlog_id = build_response["governance_backlog_items"][0]["backlog_id"]
    list_response = governance_backlog_route(status="proposed")
    update_response = update_governance_backlog_status_route(
        backlog_id,
        GovernanceBacklogStatusUpdateRequest(
            new_status="accepted",
            note="Accepted for route test.",
        ),
    )
    summary_response = governance_backlog_summary_route()

    assert build_response["backlog_summary"]["total_items"] == 1
    assert list_response["governance_backlog_items"][0]["backlog_id"] == backlog_id
    assert update_response["update_result"]["status"] == "success"
    assert summary_response["backlog_summary"]["by_status"] == {"accepted": 1}


def test_governance_portfolio_and_snapshot_routes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(
        progress_snapshot_service,
        "PROGRESS_SNAPSHOT_DIR",
        tmp_path / "progress_snapshots",
    )
    backlog_item = {
        "backlog_id": "backlog_portfolio_1",
        "object_type": "table",
        "object_name": "sales_order",
        "gap_type": "standard_mapping_gap",
        "action": "Review and confirm standard mappings",
        "owner_role": "business_data_steward",
        "priority": "key_tracking",
        "status": "proposed",
        "created_at": "2026-05-01T00:00:00",
    }
    sla_status = {
        "backlog_id": "backlog_portfolio_1",
        "due_date": "2026-05-18",
        "age_days": 19,
        "overdue_days": 2,
        "is_overdue": True,
        "sla_status": "overdue",
    }

    portfolio_response = assess_governance_portfolio_route(
        GovernancePortfolioAssessmentRequest(
            governance_backlog_items=[backlog_item],
            backlog_sla_statuses=[sla_status],
        )
    )
    snapshot_response = generate_progress_snapshot_route(
        ProgressSnapshotRequest(
            governance_backlog_items=[backlog_item],
            backlog_sla_statuses=[sla_status],
            save=True,
        )
    )
    snapshots_response = governance_progress_snapshots_route()
    summary_response = governance_portfolio_summary_route()

    assert portfolio_response["governance_portfolio_summary"]["overdue_count"] == 1
    assert portfolio_response["progress_snapshot"]["overdue_count"] == 1
    assert snapshot_response["progress_snapshot"]["total_backlog_items"] == 1
    assert snapshot_response["saved"]["status"] == "success"
    assert snapshots_response["snapshot_count"] == 1
    assert "governance_portfolio_summary" in summary_response
