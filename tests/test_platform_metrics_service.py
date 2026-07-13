"""Tests for platform-wide local data metrics."""

from pathlib import Path

from app.core.audit import trace_store
from app.core.governance import backlog_store
from app.core.governance import platform_metrics_service as metrics_service
from app.core.governance import project_workspace_service as workspace_service
from app.core.models.execution_trace import ExecutionTrace
from app.core.models.governance_backlog_item import GovernanceBacklogItem


def _patch_runtime_paths(tmp_path: Path, monkeypatch) -> None:
    workspace_dir = tmp_path / "project_workspaces"
    backlog_dir = tmp_path / "governance_backlog"
    monkeypatch.setattr(workspace_service, "PROJECT_WORKSPACE_DIR", workspace_dir)
    monkeypatch.setattr(
        workspace_service,
        "PROJECT_WORKSPACE_INDEX_PATH",
        workspace_dir / "workspace_index.json",
    )
    monkeypatch.setattr(
        workspace_service,
        "PROJECT_WORKSPACE_SNAPSHOT_DIR",
        workspace_dir / "_snapshots",
    )
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
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(metrics_service, "OUTPUTS_DIR", tmp_path / "outputs")


def _backlog_item(backlog_id: str, status: str) -> GovernanceBacklogItem:
    return GovernanceBacklogItem(
        backlog_id=backlog_id,
        object_type="table",
        object_name="customer",
        gap_type="quality_rule_gap",
        action="Add quality rules",
        owner_role="data_steward",
        priority="high",
        status=status,
        created_at="2026-06-29T10:00:00Z",
        updated_at="2026-06-29T11:00:00Z",
    )


def _kpi(metrics, name: str) -> int | float | str:  # noqa: ANN001
    return next(item.value for item in metrics.kpis if item.name == name)


def test_collect_platform_metrics_aggregates_local_runtime_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_paths(tmp_path, monkeypatch)
    workspace = workspace_service.create_project_workspace(
        "Customer cleanup",
        owner_role="data_steward",
    )
    run = workspace_service.record_project_run(
        workspace.workspace_id,
        workflow_profile="governance_readiness",
        status="success",
        result_summary={"issue_count": 3},
    )
    workspace_service.set_project_review_state(
        workspace.workspace_id,
        queue_name="quality_rules",
        pending_count=2,
        needs_business_confirmation_count=1,
    )
    workspace_service.attach_project_artifact(
        workspace.workspace_id,
        artifact_type="report",
        path="outputs/reports/customer.md",
        source_run_id=run.run_id,
    )
    backlog_store.save_backlog_items(
        [_backlog_item("backlog-1", "blocked"), _backlog_item("backlog-2", "completed")]
    )
    trace_store.save_trace(
        ExecutionTrace(
            trace_id="trace-1",
            tool_name="run_governance_profile",
            status="success",
            started_at="2026-06-29T12:00:00Z",
            finished_at="2026-06-29T12:01:00Z",
        )
    )
    output_path = metrics_service.OUTPUTS_DIR / "reports" / "customer.md"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("report", encoding="utf-8")

    metrics = metrics_service.collect_platform_metrics()

    assert _kpi(metrics, "project_workspaces") == 1
    assert _kpi(metrics, "workspace_runs") == 1
    assert _kpi(metrics, "pending_reviews") == 3
    assert _kpi(metrics, "workspace_artifacts") == 1
    assert _kpi(metrics, "backlog_items") == 2
    assert _kpi(metrics, "execution_traces") == 1
    assert _kpi(metrics, "output_files") == 1
    assert metrics.workspace_metrics[0].pending_review_count == 3
    assert metrics.workspace_metrics[0].delivery_completeness_score == 50
    assert metrics.workspace_metrics[0].delivery_completeness_level == "partial"
    assert "确认工作簿" in metrics.workspace_metrics[0].missing_delivery_components
    assert metrics.run_status_distribution[0].name == "success"
    assert metrics.workflow_profile_distribution[0].name == "governance_readiness"
    assert metrics.artifact_type_distribution[0].name == "report"
    assert {item.name for item in metrics.backlog_status_distribution} == {
        "blocked",
        "completed",
    }
    assert metrics.trace_tool_distribution[0].name == "run_governance_profile"
    assert metrics.output_inventory[0].bucket == "reports"
    assert any(
        signal.signal_type == "blocked_backlog" for signal in metrics.health_signals
    )
    assert metrics.recent_activities[0].activity_type in {
        "trace",
        "backlog",
        "workspace",
    }

def test_collect_platform_metrics_reads_configured_trace_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_paths(tmp_path, monkeypatch)
    configured_dir = tmp_path / "configured_traces"
    monkeypatch.setenv(trace_store.TRACE_DIR_ENV, str(configured_dir))
    trace_store.save_trace(
        ExecutionTrace(
            trace_id="configured-trace-1",
            tool_name="configured_trace_dir",
            status="success",
            started_at="2026-06-29T12:00:00Z",
        )
    )

    metrics = metrics_service.collect_platform_metrics()

    assert _kpi(metrics, "execution_traces") == 1
    assert (configured_dir / "configured-trace-1.json").exists()

def test_collect_platform_metrics_applies_status_filters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_paths(tmp_path, monkeypatch)
    active_workspace = workspace_service.create_project_workspace("Active workspace")
    paused_workspace = workspace_service.create_project_workspace("Paused workspace")
    paused_workspace.status = "paused"
    workspace_service.save_project_workspace(paused_workspace)
    workspace_service.record_project_run(
        active_workspace.workspace_id,
        workflow_profile="diagnosis",
        status="success",
    )
    backlog_store.save_backlog_items(
        [_backlog_item("backlog-1", "blocked"), _backlog_item("backlog-2", "completed")]
    )
    trace_store.save_trace(
        ExecutionTrace(
            trace_id="trace-success",
            tool_name="tool_a",
            status="success",
            started_at="2026-06-29T12:00:00Z",
        )
    )
    trace_store.save_trace(
        ExecutionTrace(
            trace_id="trace-failed",
            tool_name="tool_b",
            status="failed",
            started_at="2026-06-29T12:01:00Z",
        )
    )

    metrics = metrics_service.collect_platform_metrics(
        workspace_statuses=["active"],
        backlog_statuses=["blocked"],
        trace_statuses=["failed"],
        recent_activity_limit=2,
    )

    assert _kpi(metrics, "project_workspaces") == 1
    assert metrics.workspace_metrics[0].workspace_id == active_workspace.workspace_id
    assert [item.name for item in metrics.backlog_status_distribution] == ["blocked"]
    assert [item.name for item in metrics.trace_status_distribution] == ["failed"]
    assert _kpi(metrics, "execution_traces") == 1
    assert len(metrics.recent_activities) <= 2
    assert any(signal.signal_type == "trace_failure" for signal in metrics.health_signals)
    assert any(
        signal.signal_type == "run_without_artifacts"
        for signal in metrics.health_signals
    )
    assert any(
        signal.signal_type == "low_delivery_completeness"
        for signal in metrics.health_signals
    )


def test_collect_platform_metrics_reports_ok_health_when_no_risks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_paths(tmp_path, monkeypatch)

    metrics = metrics_service.collect_platform_metrics()

    assert [signal.signal_type for signal in metrics.health_signals] == [
        "platform_health"
    ]
    assert metrics.health_signals[0].severity == "ok"
