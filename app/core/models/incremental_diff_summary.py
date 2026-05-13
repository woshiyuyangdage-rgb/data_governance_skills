"""Incremental diff summary model."""

from pydantic import BaseModel


class IncrementalDiffSummary(BaseModel):
    """Count summary for incremental rerun diff categories."""

    total_objects: int
    new_count: int
    changed_count: int
    unchanged_count: int
    removed_count: int
    pending_review_count: int
    summary: str | None = None

