"""Governance backlog item model."""

from pydantic import BaseModel, Field


class GovernanceBacklogItem(BaseModel):
    """Trackable local governance backlog item derived from remediation actions."""

    backlog_id: str
    object_type: str
    object_name: str
    gap_type: str
    category: str | None = None
    action: str
    owner_role: str
    priority: str
    status: str
    urgency_score: int | None = None
    dependency_notes: str | None = None
    blocked_by: list[str] = Field(default_factory=list)
    completion_criteria: str | None = None
    expected_output: str | None = None
    reason: str | None = None
    source_signals: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    notes: str | None = None

