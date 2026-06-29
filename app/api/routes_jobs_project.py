"""Project workspace job routes."""

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    ProjectWorkspaceArtifactRequest,
    ProjectWorkspaceCreateRequest,
    ProjectWorkspaceReviewStateRequest,
    ProjectWorkspaceRunRecordRequest,
)
from app.core.governance.project_workspace_service import (
    attach_project_artifact,
    create_project_workspace,
    list_project_workspaces,
    load_project_workspace,
    record_project_run,
    set_project_review_state,
    summarize_project_workspace,
)

router = APIRouter()


@router.get("/project-workspaces")
def project_workspaces_route() -> dict[str, object]:
    """List local governance project workspaces."""
    summaries = list_project_workspaces()
    return {
        "message": "Project workspaces were loaded successfully.",
        "workspace_count": len(summaries),
        "project_workspaces": [summary.model_dump() for summary in summaries],
    }


@router.post("/project-workspaces")
def create_project_workspace_route(
    payload: ProjectWorkspaceCreateRequest,
) -> dict[str, object]:
    """Create one local governance project workspace."""
    workspace = create_project_workspace(**payload.model_dump(exclude_none=True))
    return {
        "message": f"Project workspace '{workspace.workspace_id}' was created.",
        "project_workspace": workspace.model_dump(),
    }


@router.get("/project-workspaces/{workspace_id}")
def project_workspace_detail_route(workspace_id: str) -> dict[str, object]:
    """Load one local governance project workspace."""
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Project workspace was not found.")
    summary = summarize_project_workspace(workspace_id)
    return {
        "message": f"Project workspace '{workspace_id}' was loaded.",
        "project_workspace": workspace.model_dump(),
        "project_workspace_summary": summary.model_dump() if summary else None,
    }


@router.post("/project-workspaces/{workspace_id}/runs")
def record_project_workspace_run_route(
    workspace_id: str,
    payload: ProjectWorkspaceRunRecordRequest,
) -> dict[str, object]:
    """Record one workflow run in a project workspace."""
    try:
        run = record_project_run(
            workspace_id,
            **payload.model_dump(exclude_none=True),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Project workspace was not found.",
        ) from exc
    summary = summarize_project_workspace(workspace_id)
    return {
        "message": f"Run '{run.run_id}' was recorded.",
        "project_run": run.model_dump(),
        "project_workspace_summary": summary.model_dump() if summary else None,
    }


@router.post("/project-workspaces/{workspace_id}/review-state")
def set_project_workspace_review_state_route(
    workspace_id: str,
    payload: ProjectWorkspaceReviewStateRequest,
) -> dict[str, object]:
    """Set one review queue state in a project workspace."""
    try:
        state = set_project_review_state(
            workspace_id,
            **payload.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Project workspace was not found.",
        ) from exc
    summary = summarize_project_workspace(workspace_id)
    return {
        "message": f"Review queue '{state.queue_name}' was updated.",
        "project_review_state": state.model_dump(),
        "project_workspace_summary": summary.model_dump() if summary else None,
    }


@router.post("/project-workspaces/{workspace_id}/artifacts")
def attach_project_workspace_artifact_route(
    workspace_id: str,
    payload: ProjectWorkspaceArtifactRequest,
) -> dict[str, object]:
    """Attach one local artifact to a project workspace."""
    try:
        artifact = attach_project_artifact(
            workspace_id,
            **payload.model_dump(exclude_none=True),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Project workspace was not found.",
        ) from exc
    summary = summarize_project_workspace(workspace_id)
    return {
        "message": f"Artifact '{artifact.artifact_id}' was attached.",
        "project_artifact": artifact.model_dump(),
        "project_workspace_summary": summary.model_dump() if summary else None,
    }
