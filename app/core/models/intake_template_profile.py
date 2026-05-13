"""Metadata intake template profile model."""

from pydantic import BaseModel, Field


class IntakeTemplateProfile(BaseModel):
    """Rule-based profile for one structured metadata intake template."""

    profile_name: str
    enabled: bool
    description: str
    file_types: list[str] = Field(default_factory=list)
    sheet_candidates: list[str] = Field(default_factory=list)
    required_target_fields: list[str] = Field(default_factory=list)
    optional_target_fields: list[str] = Field(default_factory=list)
    mapping_spec_name: str

