"""Batch run result model."""

from pydantic import BaseModel, Field

from app.core.models.batch_group_result import BatchGroupResult
from app.core.models.incremental_diff_summary import IncrementalDiffSummary


class BatchRunResult(BaseModel):
    """Top-level summary for a batch governance run."""

    batch_name: str
    group_results: list[BatchGroupResult] = Field(default_factory=list)
    diff_summary: IncrementalDiffSummary | None = None
    status: str
    message: str | None = None

