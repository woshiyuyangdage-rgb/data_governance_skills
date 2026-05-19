"""Configured product-level governance skill definition."""

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """Metadata for one product-level governance skill."""

    name: str
    version: str
    enabled: bool = True
    description: str
    purpose: str = ""
    primary_profiles: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    core_modules: list[str] = Field(default_factory=list)
    config_assets: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
