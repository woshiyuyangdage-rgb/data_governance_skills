"""Exported tool schema model for adapter-layer views."""

from pydantic import BaseModel, Field


class ExportedToolSchema(BaseModel):
    """One exported tool schema in the adapter layer."""

    tool_name: str
    description: str
    input_model: str | None = None
    output_model: str | None = None
    input_schema: dict[str, object]
    output_schema: dict[str, object] | None = None
    category: str | None = None
    examples: list[dict[str, object]] = Field(default_factory=list)
