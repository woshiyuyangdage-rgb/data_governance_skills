"""Project workspace route tests."""

from pathlib import Path

from app.api.routes_jobs import (
    ProjectWorkspaceArtifactRequest,
    ProjectWorkspaceCreateRequest,
    ProjectWorkspaceReviewStateRequest,
    ProjectWorkspaceRunRecordRequest,
    attach_project_workspace_artifact_route,
    create_project_workspace_route,
    project_workspace_detail_route,
    project_workspaces_route,
    record_project_workspace_run_route,
    set_project_workspace_review_state_route,
)
from app.core.governance import project_workspace_service


def test_project_workspace_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_workspace_service, "PROJECT_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(
        project_workspace_service,
        "PROJECT_WORKSPACE_INDEX_PATH",
        tmp_path / "index.json",
    )
    monkeypatch.setattr(
        project_workspace_service,
        "PROJECT_WORKSPACE_SNAPSHOT_DIR",
        tmp_path / "_snapshots",
    )

    create_response = create_project_workspace_route(
        ProjectWorkspaceCreateRequest(
            name="Customer cleanup",
            owner_role="data_steward",
            domain_pack_name="customer_domain",
        )
    )
    workspace_id = create_response["project_workspace"]["workspace_id"]
    run_response = record_project_workspace_run_route(
        workspace_id,
        ProjectWorkspaceRunRecordRequest(
            workflow_profile="diagnosis_mapping_stg_quality",
            status="completed",
            input_file_path="sample.csv",
            result_summary={"issue_count": 2},
        ),
    )
    artifact_response = attach_project_workspace_artifact_route(
        workspace_id,
        ProjectWorkspaceArtifactRequest(
            artifact_type="report",
            path="outputs/reports/customer.md",
            source_run_id=run_response["project_run"]["run_id"],
        ),
    )
    review_response = set_project_workspace_review_state_route(
        workspace_id,
        ProjectWorkspaceReviewStateRequest(
            queue_name="quality_rules",
            pending_count=1,
            needs_business_confirmation_count=1,
        ),
    )
    list_response = project_workspaces_route()
    detail_response = project_workspace_detail_route(workspace_id)

    assert list_response["workspace_count"] == 1
    assert detail_response["project_workspace"]["workspace_id"] == workspace_id
    assert artifact_response["project_workspace_summary"]["artifact_count"] == 1
    assert review_response["project_workspace_summary"]["pending_review_count"] == 2
