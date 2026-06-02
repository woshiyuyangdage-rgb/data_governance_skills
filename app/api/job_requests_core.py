"""Core workflow and intent request models."""

from typing import Any

from pydantic import BaseModel, Field


class FileRunRequest(BaseModel):
    """Request body for running the pipeline from a local file."""

    file_path: str


class ManualMetadataRequest(BaseModel):
    """Request body for small hand-entered metadata inputs."""

    records: list[dict[str, Any]] = Field(default_factory=list)
    output_dir: str | None = None
    base_filename: str | None = None


class ManualMetadataRunRequest(ManualMetadataRequest):
    """Request body for running a workflow from manual metadata rows."""

    profile_name: str = "metadata_diagnosis_only"
    apply_review_replay: bool = False
    export_reports: bool = False
    preferred_result_mode: str | None = None


class IntentTextRequest(BaseModel):
    """Request body for interpreting a natural-language governance task."""

    text: str
    file_path: str | None = None
