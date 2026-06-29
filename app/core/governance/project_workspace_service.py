"""Local JSON service for governance project workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.core.models.project_workspace import (
    ProjectWorkspace,
    ProjectWorkspaceArtifact,
    ProjectWorkspaceReviewState,
    ProjectWorkspaceRun,
    ProjectWorkspaceSummary,
)
from app.core.utils.file_utils import ensure_directory, sanitize_filename
from app.core.utils.time_utils import utc_now_compact, utc_now_seconds

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_WORKSPACE_DIR = PROJECT_ROOT / "app" / "data" / "project_workspaces"
PROJECT_WORKSPACE_INDEX_PATH = PROJECT_WORKSPACE_DIR / "workspace_index.json"
PROJECT_WORKSPACE_SNAPSHOT_DIR = PROJECT_WORKSPACE_DIR / "_snapshots"


def _utc_now() -> str:
    return utc_now_seconds()


def _workspace_path(workspace_id: str) -> Path:
    return PROJECT_WORKSPACE_DIR / f"{sanitize_filename(workspace_id)}.json"


def _snapshot_workspace_file(workspace_id: str) -> str | None:
    path = _workspace_path(workspace_id)
    if not path.exists():
        return None
    ensure_directory(PROJECT_WORKSPACE_SNAPSHOT_DIR)
    snapshot_path = (
        PROJECT_WORKSPACE_SNAPSHOT_DIR
        / f"{utc_now_compact()}_{sanitize_filename(workspace_id)}.json"
    )
    snapshot_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return str(snapshot_path)


def _workspace_summary(workspace: ProjectWorkspace) -> ProjectWorkspaceSummary:
    pending_review_count = sum(
        review.pending_count + review.needs_business_confirmation_count
        for review in workspace.review_states
    )
    last_run_status = workspace.runs[-1].status if workspace.runs else None
    return ProjectWorkspaceSummary(
        workspace_id=workspace.workspace_id,
        name=workspace.name,
        status=workspace.status,
        owner_role=workspace.owner_role,
        domain_pack_name=workspace.domain_pack_name,
        template_name=workspace.template_name,
        run_count=len(workspace.runs),
        artifact_count=len(workspace.artifacts),
        pending_review_count=pending_review_count,
        last_run_status=last_run_status,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def _write_index(workspaces: list[ProjectWorkspace]) -> None:
    ensure_directory(PROJECT_WORKSPACE_DIR)
    summaries = [_workspace_summary(workspace) for workspace in workspaces]
    PROJECT_WORKSPACE_INDEX_PATH.write_text(
        json.dumps(
            {"workspaces": [summary.model_dump() for summary in summaries]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def rebuild_workspace_index() -> list[ProjectWorkspaceSummary]:
    """Rebuild the workspace index by scanning workspace JSON files."""
    ensure_directory(PROJECT_WORKSPACE_DIR)
    workspaces = []
    for path in sorted(PROJECT_WORKSPACE_DIR.glob("*.json")):
        if path == PROJECT_WORKSPACE_INDEX_PATH:
            continue
        try:
            workspaces.append(
                ProjectWorkspace.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            )
        except (json.JSONDecodeError, ValueError):
            continue
    _write_index(workspaces)
    return [_workspace_summary(workspace) for workspace in workspaces]


def list_project_workspaces() -> list[ProjectWorkspaceSummary]:
    """List local project workspaces, newest updated first."""
    if not PROJECT_WORKSPACE_INDEX_PATH.exists():
        return rebuild_workspace_index()
    try:
        payload = json.loads(PROJECT_WORKSPACE_INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return rebuild_workspace_index()
    records = payload.get("workspaces", []) if isinstance(payload, dict) else []
    summaries = [
        ProjectWorkspaceSummary.model_validate(record)
        for record in records
        if isinstance(record, dict)
    ]
    return sorted(
        summaries,
        key=lambda item: item.updated_at or item.created_at or "",
        reverse=True,
    )


def load_project_workspace(workspace_id: str) -> ProjectWorkspace | None:
    """Load one project workspace by id."""
    path = _workspace_path(workspace_id)
    if not path.exists():
        return None
    try:
        return ProjectWorkspace.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, ValueError):
        return None


def save_project_workspace(workspace: ProjectWorkspace) -> dict[str, object]:
    """Save a project workspace and refresh the compact index."""
    ensure_directory(PROJECT_WORKSPACE_DIR)
    snapshot_path = _snapshot_workspace_file(workspace.workspace_id)
    workspace.updated_at = _utc_now()
    _workspace_path(workspace.workspace_id).write_text(
        json.dumps(workspace.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    workspaces = [
        loaded
        for summary in list_project_workspaces()
        if summary.workspace_id != workspace.workspace_id
        for loaded in [load_project_workspace(summary.workspace_id)]
        if loaded is not None
    ]
    workspaces.append(workspace)
    _write_index(workspaces)
    return {
        "workspace_id": workspace.workspace_id,
        "path": str(_workspace_path(workspace.workspace_id)),
        "snapshot_path": snapshot_path,
    }


def create_project_workspace(
    name: str,
    *,
    workspace_id: str | None = None,
    description: str | None = None,
    owner_role: str | None = None,
    domain_pack_name: str | None = None,
    template_name: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> ProjectWorkspace:
    """Create and persist a new local governance project workspace."""
    now = _utc_now()
    base_id = workspace_id or f"{sanitize_filename(name)}-{uuid4().hex[:8]}"
    workspace = ProjectWorkspace(
        workspace_id=sanitize_filename(base_id),
        name=name,
        description=description,
        owner_role=owner_role,
        domain_pack_name=domain_pack_name,
        template_name=template_name,
        created_at=now,
        updated_at=now,
        tags=list(tags or []),
        notes=notes,
    )
    save_project_workspace(workspace)
    return workspace


def record_project_run(
    workspace_id: str,
    *,
    workflow_profile: str,
    status: str,
    input_file_path: str | None = None,
    result_summary: dict[str, object] | None = None,
    artifact_ids: list[str] | None = None,
    notes: str | None = None,
) -> ProjectWorkspaceRun:
    """Append one workflow run to a project workspace."""
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        raise KeyError(workspace_id)
    run = ProjectWorkspaceRun(
        run_id=f"run-{utc_now_compact()}-{uuid4().hex[:6]}",
        workflow_profile=workflow_profile,
        status=status,
        input_file_path=input_file_path,
        result_summary=dict(result_summary or {}),
        artifact_ids=list(artifact_ids or []),
        created_at=_utc_now(),
        notes=notes,
    )
    workspace.runs.append(run)
    save_project_workspace(workspace)
    return run


def set_project_review_state(
    workspace_id: str,
    *,
    queue_name: str,
    pending_count: int = 0,
    accepted_count: int = 0,
    edited_count: int = 0,
    rejected_count: int = 0,
    needs_business_confirmation_count: int = 0,
) -> ProjectWorkspaceReviewState:
    """Set review queue counts for one project workspace."""
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        raise KeyError(workspace_id)
    state = ProjectWorkspaceReviewState(
        queue_name=queue_name,
        pending_count=max(0, pending_count),
        accepted_count=max(0, accepted_count),
        edited_count=max(0, edited_count),
        rejected_count=max(0, rejected_count),
        needs_business_confirmation_count=max(
            0,
            needs_business_confirmation_count,
        ),
        updated_at=_utc_now(),
    )
    workspace.review_states = [
        item for item in workspace.review_states if item.queue_name != queue_name
    ]
    workspace.review_states.append(state)
    save_project_workspace(workspace)
    return state


def attach_project_artifact(
    workspace_id: str,
    *,
    artifact_type: str,
    path: str,
    label: str | None = None,
    source_run_id: str | None = None,
) -> ProjectWorkspaceArtifact:
    """Attach one local report, workbook, package, or manifest to a workspace."""
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        raise KeyError(workspace_id)
    artifact = ProjectWorkspaceArtifact(
        artifact_id=f"artifact-{uuid4().hex[:10]}",
        artifact_type=artifact_type,
        path=path,
        label=label,
        source_run_id=source_run_id,
        created_at=_utc_now(),
    )
    workspace.artifacts.append(artifact)
    if source_run_id:
        for run in workspace.runs:
            if run.run_id == source_run_id and artifact.artifact_id not in run.artifact_ids:
                run.artifact_ids.append(artifact.artifact_id)
    save_project_workspace(workspace)
    return artifact


def summarize_project_workspace(workspace_id: str) -> ProjectWorkspaceSummary | None:
    """Return one compact workspace summary."""
    workspace = load_project_workspace(workspace_id)
    return _workspace_summary(workspace) if workspace is not None else None
