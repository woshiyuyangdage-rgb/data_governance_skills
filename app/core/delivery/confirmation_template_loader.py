"""Load confirmation workbook template profiles and mapping specs."""

from functools import lru_cache

from app.core.models.confirmation_template_profile import ConfirmationTemplateProfile
from app.core.rules.config_loader import (
    get_confirmation_workbook_mapping_specs_config,
    get_confirmation_workbook_template_profiles_config,
)


@lru_cache(maxsize=1)
def load_confirmation_template_profiles() -> list[ConfirmationTemplateProfile]:
    """Load all configured confirmation workbook template profiles."""
    config = get_confirmation_workbook_template_profiles_config()
    profiles = config.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError(
            "confirmation_workbook_template_profiles.yaml must contain a non-empty profiles list."
        )
    return [ConfirmationTemplateProfile.model_validate(item) for item in profiles]


def list_enabled_confirmation_template_profiles() -> list[ConfirmationTemplateProfile]:
    """Return enabled confirmation workbook template profiles."""
    return [profile for profile in load_confirmation_template_profiles() if profile.enabled]


def get_confirmation_template_profile(template_name: str) -> ConfirmationTemplateProfile:
    """Return one confirmation template profile by name."""
    for profile in load_confirmation_template_profiles():
        if profile.template_name == template_name:
            return profile
    raise ValueError(f"Confirmation template profile '{template_name}' was not found.")


@lru_cache(maxsize=1)
def load_confirmation_template_mapping_specs() -> dict[str, dict[str, list[str]]]:
    """Load confirmation workbook template field mapping specs."""
    config = get_confirmation_workbook_mapping_specs_config()
    specs = config.get("mapping_specs")
    if not isinstance(specs, dict) or not specs:
        raise ValueError(
            "confirmation_workbook_mapping_specs.yaml must contain non-empty mapping_specs."
        )
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

