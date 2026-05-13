"""Save and publish result model for control plane edits."""

from pydantic import BaseModel

from app.core.models.validation_result import ValidationResult


class ConfigEditResult(BaseModel):
    """Return metadata for one control plane save or publish action."""

    asset_name: str
    status: str
    message: str
    backup_path: str | None = None
    validation_result: ValidationResult | None = None
