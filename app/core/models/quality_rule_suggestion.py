"""Models for rule-based quality rule recommendations."""

from pydantic import BaseModel, Field


class QualityRuleSuggestion(BaseModel):
    """Recommended quality rule for one source field."""

    source_table_name: str
    source_field_name: str
    rule_name: str | None = None
    rule_description: str | None = None
    recommended_field_name: str | None = None
    target_table_name: str | None = None
    target_field_name: str | None = None
    rule_type: str
    rule_expression: str | None = None
    severity: str
    priority: str | None = None
    risk_level: str | None = None
    confidence: float | None = None
    requires_manual_review: bool = False
    review_priority: str | None = None
    rule_scope: str = "field"
    field_group: list[str] = Field(default_factory=list)
    recommendation_source: str
    match_basis: str | None = None
    reason: str | None = None
    export_formats: list[str] = Field(default_factory=list)
    learning_context: list[str] = Field(default_factory=list)
    notes: str | None = None
    confirmed_source: str | None = None
    review_action: str | None = None
    reviewer_note: str | None = None
    learned_support: float | None = None
    learned_confidence: float | None = None
