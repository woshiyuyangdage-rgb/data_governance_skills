"""Core workflow and intent request models."""

from pydantic import BaseModel


class FileRunRequest(BaseModel):
    """Request body for running the pipeline from a local file."""

    file_path: str


class IntentTextRequest(BaseModel):
    """Request body for interpreting a natural-language governance task."""

    text: str
    file_path: str | None = None
