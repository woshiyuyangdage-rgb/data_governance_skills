"""Unified governance task response model."""

from pydantic import BaseModel, Field

from app.core.models.workflow_result import WorkflowResult


class GovernanceTaskResponse(BaseModel):
    """Normalized task response returned by the governance router."""

    profile_name: str
    status: str
    message: str
    stages_executed: list[str] = Field(default_factory=list)
    result: WorkflowResult | dict[str, object]
    exported_files: dict[str, str] | None = None
