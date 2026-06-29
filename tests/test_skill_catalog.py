"""Tests for the product-level governance skill catalog."""

from app.api.routes_skills import list_skills
from app.core.skills.data_quality_rule_skill import (
    QualityRuleRecommendationSkill as NewQualityRuleRecommendationSkill,
)
from app.core.skills.data_standard_mapping_skill import (
    StandardMappingRecommendationSkill as NewStandardMappingRecommendationSkill,
)
from app.core.skills.metadata_completeness_check import (
    MetadataCompletenessCheckSkill as LegacyMetadataCompletenessCheckSkill,
)
from app.core.skills.metadata_diagnosis_skill import (
    MetadataCompletenessCheckSkill as NewMetadataCompletenessCheckSkill,
)
from app.core.skills.quality_rule_recommendation import (
    QualityRuleRecommendationSkill as LegacyQualityRuleRecommendationSkill,
)
from app.core.skills.skill_catalog import list_enabled_skills
from app.core.skills.standard_mapping_recommendation import (
    StandardMappingRecommendationSkill as LegacyStandardMappingRecommendationSkill,
)
from app.core.skills.stg_standardization_skill import (
    StgStructureSuggestionSkill as NewStgStructureSuggestionSkill,
)
from app.core.skills.stg_structure_suggestion import (
    StgStructureSuggestionSkill as LegacyStgStructureSuggestionSkill,
)

EXPECTED_SKILL_NAMES = {
    "metadata-diagnosis-skill",
    "data-standard-mapping-skill",
    "data-quality-rule-skill",
    "dbt-governance-skill",
    "stg-standardization-skill",
    "governance-report-skill",
}

LEGACY_SKILL_MODULE_PREFIXES = (
    "app.core.skills.metadata_completeness_check",
    "app.core.skills.technical_object_identification",
    "app.core.skills.naming_standard_check",
    "app.core.skills.metadata_quality_diagnosis",
    "app.core.skills.governance_task_packaging",
    "app.core.skills.standard_mapping_recommendation",
    "app.core.skills.stg_structure_suggestion",
    "app.core.skills.quality_rule_recommendation",
    "app.core.skills.quality_rule_cross_field",
)


def test_skill_catalog_lists_six_product_skills() -> None:
    skills = list_enabled_skills()

    assert {skill.name for skill in skills} == EXPECTED_SKILL_NAMES
    assert all(skill.primary_profiles for skill in skills)
    assert all(skill.core_modules for skill in skills)


def test_skills_route_uses_product_skill_catalog() -> None:
    response = list_skills()
    items = response["items"]

    assert response["message"] == "Product-level local governance skill catalog."
    assert {item["name"] for item in items} == EXPECTED_SKILL_NAMES
    assert all("purpose" in item for item in items)


def test_legacy_skill_imports_point_to_product_packages() -> None:
    assert LegacyMetadataCompletenessCheckSkill is NewMetadataCompletenessCheckSkill
    assert LegacyStandardMappingRecommendationSkill is NewStandardMappingRecommendationSkill
    assert LegacyStgStructureSuggestionSkill is NewStgStructureSuggestionSkill
    assert LegacyQualityRuleRecommendationSkill is NewQualityRuleRecommendationSkill


def test_skill_catalog_uses_product_package_module_paths() -> None:
    core_modules = [
        module
        for skill in list_enabled_skills()
        for module in skill.core_modules
    ]

    assert not any(module in LEGACY_SKILL_MODULE_PREFIXES for module in core_modules)
