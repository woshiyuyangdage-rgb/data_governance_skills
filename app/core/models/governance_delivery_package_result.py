"""Result model for local governance delivery package builds."""

from pydantic import BaseModel, Field


class GovernanceDeliveryPackageResult(BaseModel):
    """Summary of a generated governance delivery package directory."""

    package_name: str
    output_dir: str
    generated_files: dict = Field(default_factory=dict)
    status: str
    message: str | None = None

