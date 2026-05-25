"""Structured metadata diagnosis finding model."""

from pydantic import BaseModel, Field


class MetadataDiagnosisFinding(BaseModel):
    """One structured diagnosis finding for metadata governance."""

    finding_id: str
    object_type: str
    object_name: str
    system_name: str | None = None
    business_domain: str | None = None
    issue_type: str
    severity: str
    impact_scope: str | None = None
    ai_risk: str | None = None
    evidence: list[str] = Field(default_factory=list)
    suggestion: str | None = None
    requires_manual_review: bool = False
    recommended_priority: str | None = None
    confidence: float | None = None
    evidence_details: dict[str, object] = Field(default_factory=dict)

