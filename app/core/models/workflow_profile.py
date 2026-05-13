"""Workflow profile model for governance task routing."""

from pydantic import BaseModel, Field


class WorkflowProfile(BaseModel):
    """Named workflow profile used by the governance router."""

    name: str
    enabled: bool = True
    description: str
    stages: list[str] = Field(default_factory=list)
    supports_review_replay: bool = False
    default_report_mode: str | None = None
