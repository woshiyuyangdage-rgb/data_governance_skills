"""Agent shell and tool adapter request models."""

from pydantic import BaseModel, Field


class AgentShellPlanRequest(BaseModel):
    """Request body for agent shell plan preview."""

    text: str
    file_path: str | None = None
    session_id: str | None = None


class AgentShellRunRequest(BaseModel):
    """Request body for agent shell confirm-and-run flow."""

    text: str
    file_path: str | None = None
    session_id: str | None = None
    force_run: bool = False


class NativeToolInvokeRequest(BaseModel):
    """Request body for adapter-layer native tool invocation."""

    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)


class OpenAIToolInvokeRequest(BaseModel):
    """Request body for adapter-layer OpenAI-style invocation."""

    function_name: str
    arguments_json: str | dict[str, object] | None = None
