"""Cross-field quality rule recommendation model."""

from pydantic import BaseModel, Field


class CrossFieldQualityRule(BaseModel):
    """Recommended quality rule involving multiple fields in one source table."""

    source_table_name: str
    source_field_name: str | None = None
    rule_name: str | None = None
    rule_description: str | None = None
    target_table_name: str | None = None
    target_field_name: str | None = None
    field_group: list[str] = Field(default_factory=list)
    rule_type: str
    rule_expression: str
    severity: str
    priority: str | None = None
    risk_level: str | None = None
    confidence: float | None = None
    requires_manual_review: bool = False
    review_priority: str | None = None
    rule_scope: str = "cross_field"
    recommendation_source: str
    match_basis: str | None = None
    reason: str | None = None
    export_formats: list[str] = Field(default_factory=list)
    notes: str | None = None
