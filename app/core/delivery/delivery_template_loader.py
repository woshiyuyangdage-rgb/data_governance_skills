"""Load enterprise delivery template profiles, layout specs, and bundle variants."""

from functools import lru_cache

from app.core.models.delivery_template_profile import DeliveryTemplateProfile
from app.core.rules.config_loader import (
    get_delivery_bundle_variants_config,
    get_delivery_layout_specs_config,
    get_delivery_template_profiles_config,
)


@lru_cache(maxsize=1)
def load_delivery_template_profiles() -> list[DeliveryTemplateProfile]:
    """Load all configured enterprise delivery template profiles."""
    config = get_delivery_template_profiles_config()
    profiles = config.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("delivery_template_profiles.yaml must contain a non-empty profiles list.")
    return [DeliveryTemplateProfile.model_validate(item) for item in profiles]


def list_enabled_delivery_template_profiles() -> list[DeliveryTemplateProfile]:
    """Return enabled enterprise delivery template profiles."""
    return [profile for profile in load_delivery_template_profiles() if profile.enabled]


def get_delivery_template_profile(template_name: str) -> DeliveryTemplateProfile:
    """Return one enterprise delivery template profile by name."""
    for profile in load_delivery_template_profiles():
        if profile.template_name == template_name:
            return profile
    raise ValueError(f"Delivery template profile '{template_name}' was not found.")


@lru_cache(maxsize=1)
def load_delivery_layout_specs() -> dict[str, dict]:
    """Load delivery layout specs keyed by spec name."""
    config = get_delivery_layout_specs_config()
    specs = config.get("layout_specs")
    if not isinstance(specs, dict) or not specs:
        raise ValueError("delivery_layout_specs.yaml must contain non-empty layout_specs.")
    return {str(name): dict(payload or {}) for name, payload in specs.items()}


@lru_cache(maxsize=1)
def load_delivery_bundle_variants() -> dict[str, dict]:
    """Load enabled and disabled delivery bundle variants keyed by variant name."""
    config = get_delivery_bundle_variants_config()
    variants = config.get("variants")
    if not isinstance(variants, list) or not variants:
        raise ValueError("delivery_bundle_variants.yaml must contain a non-empty variants list.")
    normalized: dict[str, dict] = {}
    for item in variants:
        if not isinstance(item, dict):
            raise ValueError("Each delivery bundle variant must be a mapping.")
        variant_name = str(item.get("variant_name") or "").strip()
        if not variant_name:
            raise ValueError("Each delivery bundle variant must define variant_name.")
        normalized[variant_name] = dict(item)
    return normalized


def list_enabled_delivery_bundle_variants() -> dict[str, dict]:
    """Return enabled delivery bundle variants keyed by variant name."""
    return {
        name: payload
        for name, payload in load_delivery_bundle_variants().items()
        if bool(payload.get("enabled", False))
    }
