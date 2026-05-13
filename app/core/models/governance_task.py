"""Governance task model placeholders."""

from pydantic import BaseModel, Field


class GovernanceTask(BaseModel):
    """Basic governance task model derived from issues."""

    task_id: str
    issue_ids: list[str] = Field(default_factory=list)
    priority: str
    action: str
    suggested_owner_role: str | None = None
    acceptance_criteria: str | None = None

