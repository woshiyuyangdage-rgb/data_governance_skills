"""Models for evidence-based metadata semantic enrichment."""

from pydantic import BaseModel, Field


class FieldDescriptionSuggestion(BaseModel):
    """Evidence-based generated or optimized description for one field."""

    table_name: str
    field_name: str
    field_name_cn: str | None = None
    original_description: str | None = None
    generated_description: str
    optimized_description: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)
    governance_action: str = "manual_review"
    requires_manual_review: bool = True
    business_domain: str | None = None
    standard_code: str | None = None
    standard_name: str | None = None


class TableSemanticSummary(BaseModel):
    """Evidence-based generated or optimized semantic summary for one table."""

    table_name: str
    table_name_cn: str | None = None
    original_description: str | None = None
    business_object: str | None = None
    business_purpose: str | None = None
    core_fields: list[str] = Field(default_factory=list)
    applicable_scenarios: list[str] = Field(default_factory=list)
    ai_usage_risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    generated_summary: str
    optimized_summary: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)
    governance_action: str = "manual_review"
    requires_manual_review: bool = True
    business_domain: str | None = None
    key_concepts: list[str] = Field(default_factory=list)
