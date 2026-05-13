"""Tests for workflow profile loading."""

import pytest

from app.core.orchestrator.profile_exceptions import WorkflowProfileNotFoundError
from app.core.orchestrator.profile_loader import (
    get_workflow_profile,
    list_enabled_profiles,
    load_workflow_profiles,
)


def test_workflow_profiles_can_be_loaded() -> None:
    profiles = load_workflow_profiles()

    assert profiles
    assert any(profile.name == "metadata_diagnosis_only" for profile in profiles)
    assert any(profile.name == "diagnosis_mapping_stg_with_review" for profile in profiles)
    assert any(profile.name == "diagnosis_mapping_stg_quality" for profile in profiles)
    assert any(
        profile.name == "diagnosis_mapping_stg_quality_package_with_review"
        for profile in profiles
    )


def test_list_enabled_profiles_returns_enabled_items() -> None:
    profiles = list_enabled_profiles()

    assert profiles
    assert all(profile.enabled for profile in profiles)


def test_get_workflow_profile_raises_for_missing_profile() -> None:
    with pytest.raises(WorkflowProfileNotFoundError):
        get_workflow_profile("missing_profile")
