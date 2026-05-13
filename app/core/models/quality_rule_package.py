"""Grouped quality rule recommendation package models."""

from pydantic import BaseModel, Field

from app.core.models.quality_rule_suggestion import QualityRuleSuggestion


class QualityRulePackage(BaseModel):
    """Quality rule package for one source table."""

    source_table_name: str
    field_rule_count: int
    quality_rules: list[QualityRuleSuggestion] = Field(default_factory=list)
    summary: str
