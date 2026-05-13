"""Smoke tests for project template loading."""

from app.core.templates.project_template_loader import (
    get_project_template,
    list_enabled_project_templates,
    load_project_templates,
)


def test_project_templates_can_load() -> None:
    templates = load_project_templates()
    assert {template.template_name for template in templates} >= {
        "metadata_inventory_project",
        "standard_mapping_confirmation_project",
        "stg_structure_design_project",
        "quality_rule_build_project",
        "full_governance_delivery_project",
    }


def test_enabled_project_template_list_and_lookup() -> None:
    enabled = list_enabled_project_templates()
    assert enabled
    assert get_project_template("standard_mapping_confirmation_project").enabled is True

