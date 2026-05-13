"""Confirmed quality rule model for reviewed rule assets."""

from pydantic import BaseModel, Field


class ConfirmedQualityRule(BaseModel):
    """Reviewed quality rule ready for asset export."""

    source_table_name: str
    source_field_name: str
    recommended_field_name: str | None = None
    rule_type: str
    rule_expression: str | None = None
    severity: str
    priority: str | None = None
    rule_scope: str = "field"
    field_group: list[str] = Field(default_factory=list)
    confidence: float | None = None
    review_priority: str | None = None
    confirmation_source: str
    match_basis: str | None = None
    reason: str | None = None
    notes: str | None = None
