"""Backlog, portfolio, and progress request models."""

from pydantic import BaseModel, Field

from app.core.models.workflow_result import WorkflowResult


class GovernanceBacklogBuildRequest(BaseModel):
    """Request body for building local governance backlog items."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    remediation_actions: list[dict[str, object]] = Field(default_factory=list)
    apply_review_replay: bool = True
    persist: bool = False
    append: bool = True


class GovernanceBacklogStatusUpdateRequest(BaseModel):
    """Request body for backlog status update."""

    new_status: str
    note: str | None = None


class GovernancePortfolioAssessmentRequest(BaseModel):
    """Request body for governance portfolio assessment."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    governance_backlog_items: list[dict[str, object]] = Field(default_factory=list)
    backlog_sla_statuses: list[dict[str, object]] = Field(default_factory=list)
    apply_review_replay: bool = True
    notes: str | None = None


class ProgressSnapshotRequest(BaseModel):
    """Request body for governance progress snapshot generation."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    governance_backlog_items: list[dict[str, object]] = Field(default_factory=list)
    backlog_sla_statuses: list[dict[str, object]] = Field(default_factory=list)
    apply_review_replay: bool = True
    notes: str | None = None
    save: bool = False
