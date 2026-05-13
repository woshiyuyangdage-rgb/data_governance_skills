"""Capability manifest model for adapter-layer export."""

from pydantic import BaseModel, Field


class CapabilityManifest(BaseModel):
    """Describe the locally available governance tool platform."""

    service_name: str
    version: str
    description: str
    tools: list[dict[str, object]] = Field(default_factory=list)
    generated_at: str | None = None
