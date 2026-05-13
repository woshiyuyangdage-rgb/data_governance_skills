"""Load metadata intake profiles and mapping specs."""

from functools import lru_cache

from app.core.models.intake_template_profile import IntakeTemplateProfile
from app.core.rules.config_loader import (
    get_intake_field_mapping_specs_config,
    get_intake_template_profiles_config,
)


@lru_cache(maxsize=1)
def load_intake_template_profiles() -> list[IntakeTemplateProfile]:
    """Load all configured intake template profiles."""
    config = get_intake_template_profiles_config()
    profiles = config.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("intake_template_profiles.yaml must contain a non-empty profiles list.")
    return [IntakeTemplateProfile.model_validate(item) for item in profiles]


def list_enabled_intake_template_profiles() -> list[IntakeTemplateProfile]:
    """Return enabled intake template profiles."""
    return [profile for profile in load_intake_template_profiles() if profile.enabled]


def get_intake_template_profile(profile_name: str) -> IntakeTemplateProfile:
    """Return one intake template profile by name."""
    for profile in load_intake_template_profiles():
        if profile.profile_name == profile_name:
            return profile
    raise ValueError(f"Intake template profile '{profile_name}' was not found.")


@lru_cache(maxsize=1)
def load_intake_mapping_specs() -> dict[str, dict[str, list[str]]]:
    """Load intake field mapping specs."""
    config = get_intake_field_mapping_specs_config()
    specs = config.get("mapping_specs")
    if not isinstance(specs, dict) or not specs:
        raise ValueError("intake_field_mapping_specs.yaml must contain non-empty mapping_specs.")
    normalized: dict[str, dict[str, list[str]]] = {}
    for spec_name, mapping in specs.items():
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError(f"Mapping spec '{spec_name}' must be a non-empty mapping.")
        normalized[str(spec_name)] = {
            str(target_field): [str(alias) for alias in aliases]
            for target_field, aliases in mapping.items()
            if isinstance(aliases, list)
        }
    return normalized

