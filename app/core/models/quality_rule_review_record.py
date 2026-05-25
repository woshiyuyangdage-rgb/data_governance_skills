"""Persistable review records for quality rule recommendations."""

from pydantic import BaseModel, Field


class QualityRuleReviewRecord(BaseModel):
    """Human review decision for one recommended quality rule."""

    source_table_name: str
    source_field_name: str
    rule_name: str | None = None
    rule_description: str | None = None
    rule_scope: str = "field"
    field_group: list[str] = Field(default_factory=list)
    target_table_name: str | None = None
    target_field_name: str | None = None
    rule_type: str
    original_rule_expression: str | None = None
    final_rule_expression: str | None = None
    original_severity: str | None = None
    final_severity: str | None = None
    risk_level: str | None = None
    recommended_field_name: str | None = None
    recommendation_source: str | None = None
    match_basis: str | None = None
    export_formats: list[str] = Field(default_factory=list)
    learning_context: list[str] = Field(default_factory=list)
    review_action: str
    confidence: float | None = None
    review_priority: str | None = None
    reviewer_note: str | None = None
    reviewed_at: str | None = None
    source: str
