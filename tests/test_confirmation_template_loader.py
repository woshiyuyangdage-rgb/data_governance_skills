"""Tests for confirmation workbook template loading."""

from app.core.delivery.confirmation_template_loader import (
    get_confirmation_template_profile,
    list_enabled_confirmation_template_profiles,
    load_confirmation_template_mapping_specs,
    load_confirmation_template_profiles,
)


def test_confirmation_template_profiles_load() -> None:
    profiles = load_confirmation_template_profiles()

    assert profiles
    assert any(
        profile.template_name == "business_mapping_review_template"
        for profile in profiles
    )


def test_enabled_confirmation_template_profiles_are_listed() -> None:
    profiles = list_enabled_confirmation_template_profiles()

    assert profiles
    assert all(profile.enabled for profile in profiles)


def test_get_confirmation_template_profile_returns_one_profile() -> None:
    profile = get_confirmation_template_profile("backlog_update_template")

    assert profile.workbook_type == "backlog_confirmation"
    assert profile.mapping_spec_name == "backlog_update_spec"


def test_confirmation_template_mapping_specs_load() -> None:
    specs = load_confirmation_template_mapping_specs()

    assert "business_mapping_review_spec" in specs
    assert "confirmation_status" in specs["business_mapping_review_spec"]
