"""Compatibility wrapper for data quality rule skill modules."""

from app.core.skills.data_quality_rule_skill.quality_rule_io import (
    QualityRuleRecommendationInput,
    QualityRuleRecommendationOutput,
)
from app.core.skills.data_quality_rule_skill.quality_rule_recommendation import (
    QualityRuleRecommendationSkill,
)

__all__ = [
    "QualityRuleRecommendationInput",
    "QualityRuleRecommendationOutput",
    "QualityRuleRecommendationSkill",
]
