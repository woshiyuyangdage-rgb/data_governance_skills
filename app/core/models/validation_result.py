"""Validation result model for control plane assets."""

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Structured validation outcome for one config asset."""

    asset_name: str
    is_valid: bool
    messages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
