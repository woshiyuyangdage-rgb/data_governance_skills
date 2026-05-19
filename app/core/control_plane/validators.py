"""Validation entrypoint for control-plane managed assets."""

from collections.abc import Callable
from typing import Any

from app.core.control_plane.validators_core import CORE_VALIDATORS
from app.core.control_plane.validators_delivery import DELIVERY_VALIDATORS
from app.core.control_plane.validators_governance import GOVERNANCE_VALIDATORS
from app.core.control_plane.validators_intake import INTAKE_VALIDATORS
from app.core.control_plane.validators_quality import QUALITY_VALIDATORS
from app.core.models.validation_result import ValidationResult

Validator = Callable[[Any], ValidationResult]

ASSET_VALIDATORS: dict[str, Validator] = {
    **CORE_VALIDATORS,
    **QUALITY_VALIDATORS,
    **GOVERNANCE_VALIDATORS,
    **DELIVERY_VALIDATORS,
    **INTAKE_VALIDATORS,
}


def validate_asset_content(asset_name: str, content: Any) -> ValidationResult:
    """Validate one managed asset by its asset name."""
    validator = ASSET_VALIDATORS.get(asset_name)
    if validator is None:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=True,
            messages=[],
            warnings=[f"No dedicated validator is registered for asset '{asset_name}'."],
        )
    return validator(content)


__all__ = ["validate_asset_content"]
