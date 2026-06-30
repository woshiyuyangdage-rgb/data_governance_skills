"""Tests for project workspace timeline and run comparison insights."""

from pathlib import Path

from app.core.governance import project_workspace_insights_service as insights
from app.core.governance import project_workspace_service as service


def _isolate_workspace_store(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_SNAPSHOT_DIR", tmp_path / "_snapshots")


def test_project_workspace_run_timeline_and_comparison(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace_store(monkeypatch, tmp_path)
    workspace = service.create_project_workspace("Readiness improvement")
    first_run = service.record_project_run(
        workspace.workspace_id,
        workflow_profile="readiness",
        status="success",
        result_summary={
            "issue_count": 12,
            "mapping_count": 8,
            "quality_rule_count": 3,
            "backlog_item_count": 10,
        },
    )
    second_run = service.record_project_run(
        workspace.workspace_id,
        workflow_profile="readiness",
        status="success",
        result_summary={
            "diagnosis_issues": 5,
            "mapping_recommendations": 12,
            "quality_rule_recommendations": 9,
            "governance_backlog_items": 4,
        },
    )
    service.attach_project_artifact(
        workspace.workspace_id,
        artifact_type="report",
        path="outputs/report.md",
        source_run_id=second_run.run_id,
    )

    timeline = insights.build_project_run_timeline(workspace.workspace_id)
    comparison = insights.compare_project_workspace_runs(workspace.workspace_id)
    deltas = {item["metric"]: item for item in comparison["metric_deltas"]}

    assert timeline["run_count"] == 2
    assert timeline["runs"][0]["issue_count"] == 12
    assert timeline["runs"][1]["issue_count"] == 5
    assert timeline["runs"][1]["artifact_count"] == 1
    assert comparison["baseline_run_id"] == first_run.run_id
    assert comparison["target_run_id"] == second_run.run_id
    assert deltas["issue_count"]["delta"] == -7
    assert deltas["issue_count"]["direction"] == "improved"
    assert deltas["backlog_item_count"]["direction"] == "improved"
    assert deltas["quality_rule_count"]["delta"] == 6
    assert deltas["quality_rule_count"]["direction"] == "improved"
    assert deltas["artifact_count"]["target_value"] == 1


def test_project_workspace_comparison_handles_empty_workspace(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace_store(monkeypatch, tmp_path)
    workspace = service.create_project_workspace("No runs")

    comparison = insights.compare_project_workspace_runs(workspace.workspace_id)

    assert comparison["status"] == "insufficient_runs"
    assert comparison["metric_deltas"] == []
