"""Metadata intake template match result model."""

from pydantic import BaseModel, Field


class IntakeMatchResult(BaseModel):
    """Explainable result for matching one intake template."""

    matched_profile_name: str | None = None
    confidence: float | None = None
    matched_sheet_name: str | None = None
    matched_headers: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    message: str | None = None

