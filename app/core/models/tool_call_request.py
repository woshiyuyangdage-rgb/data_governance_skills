"""Standard request model for local governance tool calls."""

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    """Request payload for one named tool call."""

    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
