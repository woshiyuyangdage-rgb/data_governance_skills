"""Validation result for confirmation workbook imports."""

from pydantic import BaseModel, Field


class WorkbookValidationResult(BaseModel):
    """Workbook-level validation result."""

    workbook_type: str
    is_valid: bool
    detected_sheet_name: str | None = None
    required_columns_present: list[str] = Field(default_factory=list)
    missing_required_columns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)

