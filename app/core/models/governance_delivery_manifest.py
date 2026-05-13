"""Manifest model for local governance delivery packages."""

from pydantic import BaseModel, Field


class GovernanceDeliveryManifest(BaseModel):
    """Machine-readable inventory for a governance delivery package."""

    package_name: str
    generated_at: str | None = None
    included_artifacts: list[dict] = Field(default_factory=list)
    summary: str | None = None

