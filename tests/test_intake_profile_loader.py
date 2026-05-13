"""Smoke tests for metadata intake profile loading."""

from app.core.intake.intake_profile_loader import (
    get_intake_template_profile,
    list_enabled_intake_template_profiles,
    load_intake_mapping_specs,
    load_intake_template_profiles,
)


def test_intake_profiles_can_load() -> None:
    profiles = load_intake_template_profiles()
    assert {profile.profile_name for profile in profiles} >= {
        "standard_metadata_template",
        "governance_platform_export_template",
        "manual_inventory_template",
    }


def test_enabled_intake_profiles_and_mapping_specs_load() -> None:
    assert list_enabled_intake_template_profiles()
    assert get_intake_template_profile("manual_inventory_template").enabled is True
    specs = load_intake_mapping_specs()
    assert "governance_platform_export_spec" in specs

