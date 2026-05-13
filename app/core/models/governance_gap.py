"""Governance gap model."""

from pydantic import BaseModel, Field


class GovernanceGap(BaseModel):
    """Classified governance gap aggregated from workflow signals."""

    object_type: str
    object_name: str
    gap_type: str
    category: str
    severity: str
    source_signals: list[str] = Field(default_factory=list)
    reason: str | None = None
    suggested_owner_role: str | None = None
