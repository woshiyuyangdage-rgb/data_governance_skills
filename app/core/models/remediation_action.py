"""Remediation action model."""

from pydantic import BaseModel, Field


class RemediationAction(BaseModel):
    """Recommended governance remediation action."""

    object_type: str
    object_name: str
    gap_type: str
    action: str
    owner_role: str
    priority: str
    priority_score: float | None = None
    business_impact_score: float | None = None
    ai_consumption_risk_score: float | None = None
    governance_risk_score: float | None = None
    severity_score: float | None = None
    remediation_complexity_score: float | None = None
    priority_reason: str | None = None
    suggested_cycle: str | None = None
    expected_benefit: str | None = None
    expected_output: str | None = None
    dependency_notes: str | None = None
    reason: str | None = None
    affected_objects: list[str] = Field(default_factory=list)
    signal_count: int = 0
    evidence_details: dict[str, object] = Field(default_factory=dict)
