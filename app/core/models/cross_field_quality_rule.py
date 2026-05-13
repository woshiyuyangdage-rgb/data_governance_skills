"""Cross-field quality rule recommendation model."""

from pydantic import BaseModel, Field


class CrossFieldQualityRule(BaseModel):
    """Recommended quality rule involving multiple fields in one source table."""

    source_table_name: str
    field_group: list[str] = Field(default_factory=list)
    rule_type: str
    rule_expression: str
    severity: str
    priority: str | None = None
    confidence: float | None = None
    review_priority: str | None = None
    recommendation_source: str
    match_basis: str | None = None
    reason: str | None = None
    notes: str | None = None
