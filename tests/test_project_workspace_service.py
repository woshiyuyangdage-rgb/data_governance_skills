"""Tests for local governance project workspaces."""

from pathlib import Path

from app.core.governance import project_workspace_service as service


def test_project_workspace_records_runs_reviews_and_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_SNAPSHOT_DIR", tmp_path / "_snapshots")

    workspace = service.create_project_workspace(
        "Customer metadata cleanup",
        owner_role="data_steward",
        domain_pack_name="customer_domain",
        template_name="full_governance_work_package",
        tags=["customer", "ai-ready"],
    )
    run = service.record_project_run(
        workspace.workspace_id,
        workflow_profile="diagnosis_mapping_stg_quality",
        status="completed",
        input_file_path="sample.csv",
        result_summary={"issue_count": 3},
    )
    artifact = service.attach_project_artifact(
        workspace.workspace_id,
        artifact_type="report",
        path="outputs/reports/customer.md",
        label="Customer report",
        source_run_id=run.run_id,
    )
    review = service.set_project_review_state(
        workspace.workspace_id,
        queue_name="quality_rules",
        pending_count=2,
        accepted_count=1,
        needs_business_confirmation_count=1,
    )

    loaded = service.load_project_workspace(workspace.workspace_id)
    assert loaded is not None
    assert loaded.runs[0].result_summary["issue_count"] == 3
    assert loaded.artifacts[0].artifact_id == artifact.artifact_id
    assert loaded.runs[0].artifact_ids == [artifact.artifact_id]
    assert review.total_count == 4

    summary = service.summarize_project_workspace(workspace.workspace_id)
    assert summary is not None
    assert summary.run_count == 1
    assert summary.artifact_count == 1
    assert summary.pending_review_count == 3
    assert summary.last_run_status == "completed"

    listed = service.list_project_workspaces()
    assert [item.workspace_id for item in listed] == [workspace.workspace_id]


def test_project_workspace_save_creates_snapshot(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(service, "PROJECT_WORKSPACE_SNAPSHOT_DIR", tmp_path / "_snapshots")

    workspace = service.create_project_workspace("Backlog closure")
    workspace.status = "paused"
    result = service.save_project_workspace(workspace)

    assert result["snapshot_path"] is not None
    assert Path(str(result["snapshot_path"])).exists()
    assert service.load_project_workspace(workspace.workspace_id).status == "paused"
