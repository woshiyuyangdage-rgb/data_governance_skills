"""Invocation result model for adapter-layer calls."""

from pydantic import BaseModel


class AdapterInvocationResult(BaseModel):
    """Normalized wrapper around a local tool call through one adapter shape."""

    adapter_name: str
    tool_name: str
    status: str
    message: str
    tool_response: dict[str, object] | None = None
    trace_id: str | None = None
