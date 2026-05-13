"""Backlog SLA status model."""

from pydantic import BaseModel


class BacklogSlaStatus(BaseModel):
    """SLA-ready status derived from one backlog item."""

    backlog_id: str
    due_date: str | None = None
    age_days: int | None = None
    overdue_days: int | None = None
    is_overdue: bool = False
    sla_status: str | None = None
