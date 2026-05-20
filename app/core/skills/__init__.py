"""Skill placeholders for governance workflows."""

from app.core.skills.base_skill import BaseSkill
from app.core.skills.data_quality_rule_skill import QualityRuleRecommendationSkill
from app.core.skills.data_standard_mapping_skill import StandardMappingRecommendationSkill
from app.core.skills.metadata_diagnosis_skill import (
    GovernanceTaskPackagingSkill,
    MetadataCompletenessCheckSkill,
    MetadataQualityDiagnosisSkill,
    NamingStandardCheckSkill,
    TechnicalObjectIdentificationSkill,
)
from app.core.skills.skill_catalog import list_enabled_skills, load_skill_catalog
from app.core.skills.stg_standardization_skill import StgStructureSuggestionSkill

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
    "load_skill_catalog",
    "list_enabled_skills",
]
