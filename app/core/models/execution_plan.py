"""Execution plan model for the lightweight agent shell."""

from pydantic import BaseModel, Field


class ExecutionPlan(BaseModel):
    """Previewable execution plan built from intent plus task request."""

    raw_text: str
    profile_name: str
    stages: list[str] = Field(default_factory=list)
    apply_review_replay: bool = False
    export_reports: bool = False
    file_path: str | None = None
    requires_confirmation: bool = False
    validation_passed: bool = False
    validation_messages: list[str] = Field(default_factory=list)
    autofilled_parameters: dict[str, object] = Field(default_factory=dict)
    context_messages: list[str] = Field(default_factory=list)
    suggested_output_mode: str | None = None
    summary: str | None = None
