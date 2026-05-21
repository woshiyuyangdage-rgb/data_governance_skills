"""Persistable review records for quality rule recommendations."""

from pydantic import BaseModel, Field


class QualityRuleReviewRecord(BaseModel):
    """Human review decision for one recommended quality rule."""

    source_table_name: str
    source_field_name: str
    rule_scope: str = "field"
    field_group: list[str] = Field(default_factory=list)
    rule_type: str
    original_rule_expression: str | None = None
    final_rule_expression: str | None = None
    original_severity: str | None = None
    final_severity: str | None = None
    recommended_field_name: str | None = None
    recommendation_source: str | None = None
    match_basis: str | None = None
    learning_context: list[str] = Field(default_factory=list)
    review_action: str
    confidence: float | None = None
    review_priority: str | None = None
    reviewer_note: str | None = None
    reviewed_at: str | None = None
    source: str
