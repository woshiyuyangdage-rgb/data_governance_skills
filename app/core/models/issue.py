"""Issue model placeholders for governance findings."""

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """Basic issue model produced by governance rules and skills."""

    issue_id: str
    object_type: str
    object_name: str
    issue_type: str
    severity: str
    evidence: list[str] = Field(default_factory=list)
    suggestion: str | None = None
    confidence: float | None = None
    system_name: str | None = None
    business_domain: str | None = None
    impact_scope: str | None = None
    ai_risk: str | None = None
    recommended_priority: str | None = None
    requires_manual_review: bool | None = None
    evidence_details: dict[str, object] = Field(default_factory=dict)
