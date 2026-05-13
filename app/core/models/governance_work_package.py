"""Governance work package model."""

from pydantic import BaseModel, Field

from app.core.models.governance_gap import GovernanceGap
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction


class GovernanceWorkPackage(BaseModel):
    """Exportable local package for readiness and remediation planning."""

    package_name: str
    generated_at: str | None = None
    readiness_scores: list[ReadinessScore] = Field(default_factory=list)
    governance_gaps: list[GovernanceGap] = Field(default_factory=list)
    remediation_actions: list[RemediationAction] = Field(default_factory=list)
    summary: str | None = None
