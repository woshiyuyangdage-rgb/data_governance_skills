"""Models for rule-based quality rule recommendations."""

from pydantic import BaseModel, Field


class QualityRuleSuggestion(BaseModel):
    """Recommended quality rule for one source field."""

    source_table_name: str
    source_field_name: str
    recommended_field_name: str | None = None
    rule_type: str
    rule_expression: str | None = None
    severity: str
    priority: str | None = None
    confidence: float | None = None
    review_priority: str | None = None
    rule_scope: str = "field"
    field_group: list[str] = Field(default_factory=list)
    recommendation_source: str
    match_basis: str | None = None
    reason: str | None = None
    learning_context: list[str] = Field(default_factory=list)
    notes: str | None = None
    confirmed_source: str | None = None
    review_action: str | None = None
    reviewer_note: str | None = None
    learned_support: float | None = None
    learned_confidence: float | None = None
