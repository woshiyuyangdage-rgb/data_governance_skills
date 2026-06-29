"""Project workspace request models."""

from pydantic import BaseModel, Field


class ProjectWorkspaceCreateRequest(BaseModel):
    """Request body for creating a local governance project workspace."""

    name: str
    workspace_id: str | None = None
    description: str | None = None
    owner_role: str | None = None
    domain_pack_name: str | None = None
    template_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProjectWorkspaceRunRecordRequest(BaseModel):
    """Request body for recording one project workflow run."""

    workflow_profile: str
    status: str
    input_file_path: str | None = None
    result_summary: dict[str, object] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProjectWorkspaceReviewStateRequest(BaseModel):
    """Request body for setting one project review queue state."""

    queue_name: str
    pending_count: int = 0
    accepted_count: int = 0
    edited_count: int = 0
    rejected_count: int = 0
    needs_business_confirmation_count: int = 0


class ProjectWorkspaceArtifactRequest(BaseModel):
    """Request body for attaching one local artifact to a project workspace."""

    artifact_type: str
    path: str
    label: str | None = None
    source_run_id: str | None = None
