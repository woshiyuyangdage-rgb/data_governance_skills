"""Metadata intake normalization result model."""

from pydantic import BaseModel, Field

from app.core.models.intake_mapping_result import IntakeMappingResult


class IntakeNormalizationResult(BaseModel):
    """Result of normalizing an intake file into standard metadata records."""

    profile_name: str
    row_count: int
    table_count: int
    normalized_records: list[dict] = Field(default_factory=list)
    mapping_result: IntakeMappingResult | None = None
    status: str
    message: str | None = None

