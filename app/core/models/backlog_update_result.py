"""Governance backlog update result model."""

from pydantic import BaseModel


class BacklogUpdateResult(BaseModel):
    """Result returned after a local backlog status update."""

    backlog_id: str
    old_status: str | None = None
    new_status: str | None = None
    status: str
    message: str
    updated_at: str | None = None

