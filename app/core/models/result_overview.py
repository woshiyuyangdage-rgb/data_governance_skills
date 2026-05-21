"""Shared result overview model for Streamlit workbench pages."""

from typing import Any

from pydantic import BaseModel, Field


class ResultOverviewMetric(BaseModel):
    """One metric shown in a result overview."""

    label: str
    value: Any | None = None
    help_text: str | None = None


class ResultOverviewArtifact(BaseModel):
    """One file or attachment shown in a result overview."""

    label: str
    path: str | None = None
    mime: str | None = None


class ResultOverview(BaseModel):
    """Normalized summary for any page-level result."""

    title: str
    summary: str | None = None
    status: str | None = None
    details: list[tuple[str, Any | None]] = Field(default_factory=list)
    metrics: list[ResultOverviewMetric] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_step: str | None = None
    artifacts: list[ResultOverviewArtifact] = Field(default_factory=list)
