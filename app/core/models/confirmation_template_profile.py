"""Confirmation workbook template profile model."""

from pydantic import BaseModel, Field


class ConfirmationTemplateProfile(BaseModel):
    """Rule-based profile for one confirmation workbook layout."""

    template_name: str
    enabled: bool
    workbook_type: str
    description: str
    file_types: list[str] = Field(default_factory=list)
    sheet_candidates: list[str] = Field(default_factory=list)
    required_target_fields: list[str] = Field(default_factory=list)
    optional_target_fields: list[str] = Field(default_factory=list)
    mapping_spec_name: str

