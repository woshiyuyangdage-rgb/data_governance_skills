"""Skill placeholders for governance workflows."""

from app.core.skills.base_skill import BaseSkill
from app.core.skills.governance_task_packaging import GovernanceTaskPackagingSkill
from app.core.skills.metadata_completeness_check import MetadataCompletenessCheckSkill
from app.core.skills.metadata_quality_diagnosis import MetadataQualityDiagnosisSkill
from app.core.skills.naming_standard_check import NamingStandardCheckSkill
from app.core.skills.quality_rule_recommendation import QualityRuleRecommendationSkill
from app.core.skills.standard_mapping_recommendation import (
    StandardMappingRecommendationSkill,
)
from app.core.skills.stg_structure_suggestion import StgStructureSuggestionSkill
from app.core.skills.technical_object_identification import (
    TechnicalObjectIdentificationSkill,
)

__all__ = [
    "BaseSkill",
    "MetadataCompletenessCheckSkill",
    "TechnicalObjectIdentificationSkill",
    "NamingStandardCheckSkill",
    "MetadataQualityDiagnosisSkill",
    "GovernanceTaskPackagingSkill",
    "StandardMappingRecommendationSkill",
    "StgStructureSuggestionSkill",
    "QualityRuleRecommendationSkill",
]
