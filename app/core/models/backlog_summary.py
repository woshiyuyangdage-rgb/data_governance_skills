"""Governance backlog summary model."""

from pydantic import BaseModel, Field


class BacklogSummary(BaseModel):
    """Dashboard-ready backlog aggregate counts."""

    total_items: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_owner_role: dict[str, int] = Field(default_factory=dict)
    by_gap_type: dict[str, int] = Field(default_factory=dict)
    blocked_count: int = 0
    completed_count: int = 0
    summary: str | None = None

