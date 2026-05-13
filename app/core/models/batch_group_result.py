"""Batch group result model."""

from pydantic import BaseModel


class BatchGroupResult(BaseModel):
    """Summary for one processed batch group."""

    group_name: str
    file_count: int
    table_count: int
    status: str
    summary: str | None = None

