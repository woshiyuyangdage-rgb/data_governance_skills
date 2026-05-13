"""Governance readiness score model."""

from typing import Any

from pydantic import BaseModel, Field


class ReadinessScore(BaseModel):
    """Readiness score for a table, domain, or overall workflow result."""

    object_type: str
    object_name: str
    overall_score: float
    readiness_level: str
    dimension_scores: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
