"""Tests for the product-level governance skill catalog."""

from app.api.routes_skills import list_skills
from app.core.skills.skill_catalog import list_enabled_skills


EXPECTED_SKILL_NAMES = {
    "metadata-diagnosis-skill",
    "data-standard-mapping-skill",
    "data-quality-rule-skill",
    "dbt-governance-skill",
    "stg-standardization-skill",
    "governance-report-skill",
}


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
