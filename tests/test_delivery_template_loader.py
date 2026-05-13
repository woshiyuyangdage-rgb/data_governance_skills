"""Tests for enterprise delivery template loading."""

from app.core.delivery.delivery_template_loader import (
    get_delivery_template_profile,
    list_enabled_delivery_bundle_variants,
    list_enabled_delivery_template_profiles,
    load_delivery_bundle_variants,
    load_delivery_layout_specs,
    load_delivery_template_profiles,
)


def test_delivery_template_profiles_load() -> None:
    profiles = load_delivery_template_profiles()

    assert profiles
    assert any(
        profile.template_name == "business_mapping_delivery_template"
        for profile in profiles
    )


def test_enabled_delivery_template_profiles_are_listed() -> None:
    profiles = list_enabled_delivery_template_profiles()

    assert profiles
    assert all(profile.enabled for profile in profiles)


def test_delivery_layout_specs_and_variants_load() -> None:
    specs = load_delivery_layout_specs()
    variants = load_delivery_bundle_variants()

    assert "business_mapping_layout" in specs
    assert specs["business_mapping_layout"]["sheet_name"] == "mapping_review"
    assert "business_confirmation_bundle" in variants
    assert variants["business_confirmation_bundle"]["included_outputs"]


def test_get_delivery_template_profile_returns_one_profile() -> None:
    profile = get_delivery_template_profile("architecture_stg_delivery_template")

    assert profile.target_artifact_type == "stg_confirmation_workbook"
    assert profile.layout_spec_name == "architecture_stg_layout"


def test_enabled_delivery_bundle_variants_are_listed() -> None:
    variants = list_enabled_delivery_bundle_variants()

    assert "standard_delivery_bundle" in variants
    assert all(payload.get("enabled") for payload in variants.values())
