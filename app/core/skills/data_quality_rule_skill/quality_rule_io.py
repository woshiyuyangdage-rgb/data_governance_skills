"""Input and output models for data quality rule recommendation."""

from pydantic import BaseModel, Field

from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta


class QualityRuleRecommendationInput(BaseModel):
    """Input schema for quality rule recommendation."""

    tables: list[TableMeta] = Field(default_factory=list)
    confirmed_mapping_results: list[MappingResult] = Field(default_factory=list)
    mapping_results: list[MappingResult] = Field(default_factory=list)
    confirmed_stg_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    stg_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    domain_pack_hints: dict = Field(default_factory=dict)


class QualityRuleRecommendationOutput(BaseModel):
    """Output schema for quality rule recommendation."""

    quality_rule_suggestions: list[QualityRuleSuggestion] = Field(default_factory=list)
    cross_field_quality_rules: list[CrossFieldQualityRule] = Field(default_factory=list)
    quality_rule_packages: list[QualityRulePackage] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""
