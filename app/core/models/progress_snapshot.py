"""Governance progress snapshot model."""

from pydantic import BaseModel


class ProgressSnapshot(BaseModel):
    """Point-in-time trend-ready progress snapshot."""

    snapshot_id: str
    generated_at: str | None = None
    total_backlog_items: int
    completed_count: int
    blocked_count: int
    overdue_count: int
    avg_readiness_score: float | None = None
    notes: str | None = None
