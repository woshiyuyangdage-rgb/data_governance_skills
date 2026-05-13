"""Incremental diff item model."""

from pydantic import BaseModel


class IncrementalDiffItem(BaseModel):
    """Before/after fingerprint comparison for one metadata object."""

    object_type: str
    object_name: str
    group_name: str | None = None
    diff_type: str
    reason: str | None = None
    old_fingerprint: str | None = None
    new_fingerprint: str | None = None

