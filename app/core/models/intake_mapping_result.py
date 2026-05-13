"""Metadata intake column mapping result model."""

from pydantic import BaseModel, Field


class IntakeMappingResult(BaseModel):
    """Column-level mapping result for intake normalization."""

    profile_name: str
    source_columns: list[str] = Field(default_factory=list)
    mapped_fields: dict = Field(default_factory=dict)
    unmapped_source_columns: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    status: str
    message: str | None = None

