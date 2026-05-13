"""Governance portfolio summary model."""

from pydantic import BaseModel, Field


class GovernancePortfolioSummary(BaseModel):
    """Dashboard-ready aggregate for governance portfolio management."""

    total_items: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_owner_role: dict[str, int] = Field(default_factory=dict)
    by_gap_type: dict[str, int] = Field(default_factory=dict)
    readiness_distribution: dict[str, int] = Field(default_factory=dict)
    overdue_count: int = 0
    blocked_count: int = 0
    owner_workload: dict[str, dict[str, int]] = Field(default_factory=dict)
    summary: str | None = None
