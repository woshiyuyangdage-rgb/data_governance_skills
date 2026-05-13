"""Resolved execution context for local agent shell requests."""

from pydantic import BaseModel, Field


class ResolvedContext(BaseModel):
    """Describe how session-scoped context parameters were resolved."""

    session_id: str | None = None
    resolved_file_path: str | None = None
    resolved_output_dir: str | None = None
    resolved_from: list[str] = Field(default_factory=list)
    reference_matches: list[str] = Field(default_factory=list)
    autofilled_parameters: dict[str, object] = Field(default_factory=dict)
    ambiguity_detected: bool = False
    messages: list[str] = Field(default_factory=list)
