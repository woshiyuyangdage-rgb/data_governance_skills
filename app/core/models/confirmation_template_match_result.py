"""Confirmation workbook template match result model."""

from pydantic import BaseModel, Field


class ConfirmationTemplateMatchResult(BaseModel):
    """Explainable result for confirmation workbook template diagnosis."""

    matched_template_name: str | None = None
    workbook_type: str | None = None
    confidence: float | None = None
    matched_sheet_name: str | None = None
    matched_headers: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    unmapped_source_columns: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)
    message: str | None = None

