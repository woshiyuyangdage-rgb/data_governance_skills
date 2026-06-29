"""Governance project workspace models."""

from pydantic import BaseModel, Field


class ProjectWorkspaceArtifact(BaseModel):
    """One local artifact attached to a governance project workspace."""

    artifact_id: str
    artifact_type: str
    path: str
    label: str | None = None
    source_run_id: str | None = None
    created_at: str | None = None


class ProjectWorkspaceRun(BaseModel):
    """One workflow run recorded inside a project workspace."""

    run_id: str
    workflow_profile: str
    status: str
    input_file_path: str | None = None
    result_summary: dict[str, object] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None
    notes: str | None = None


class ProjectWorkspaceReviewState(BaseModel):
    """Review queue counts for one project workspace."""

    queue_name: str
    pending_count: int = 0
    accepted_count: int = 0
    edited_count: int = 0
    rejected_count: int = 0
    needs_business_confirmation_count: int = 0
    updated_at: str | None = None

    @property
    def total_count(self) -> int:
        """Return total known review items in this queue."""
        return (
            self.pending_count
            + self.accepted_count
            + self.edited_count
            + self.rejected_count
            + self.needs_business_confirmation_count
        )


class ProjectWorkspace(BaseModel):
    """Durable local project workspace for a governance initiative."""

    workspace_id: str
    name: str
    description: str | None = None
    owner_role: str | None = None
    domain_pack_name: str | None = None
    template_name: str | None = None
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None
    runs: list[ProjectWorkspaceRun] = Field(default_factory=list)
    review_states: list[ProjectWorkspaceReviewState] = Field(default_factory=list)
    artifacts: list[ProjectWorkspaceArtifact] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProjectWorkspaceSummary(BaseModel):
    """Compact index entry for listing governance project workspaces."""

    workspace_id: str
    name: str
    status: str
    owner_role: str | None = None
    domain_pack_name: str | None = None
    template_name: str | None = None
    run_count: int = 0
    artifact_count: int = 0
    pending_review_count: int = 0
    last_run_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
