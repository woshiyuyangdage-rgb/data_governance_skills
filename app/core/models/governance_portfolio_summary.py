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
    high_risk_item_count: int = 0
    critical_risk_item_count: int = 0
    avg_priority_score: float | None = None
    avg_ai_consumption_risk_score: float | None = None
    risk_tier_distribution: dict[str, int] = Field(default_factory=dict)
    top_risk_items: list[dict[str, object]] = Field(default_factory=list)
    owner_workload: dict[str, dict[str, int]] = Field(default_factory=dict)
    summary: str | None = None
