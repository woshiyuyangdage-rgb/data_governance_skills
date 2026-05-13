"""Standard response model for local governance tool calls."""

from pydantic import BaseModel


class ToolCallResponse(BaseModel):
    """Normalized response returned by the tool executor."""

    tool_name: str
    status: str
    message: str
    result: dict[str, object] | list[object] | None = None
    trace_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
