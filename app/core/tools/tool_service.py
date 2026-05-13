"""Thin service layer for local governance tool execution."""

from app.core.models.tool_call_request import ToolCallRequest
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.tool_definition import ToolDefinition
from app.core.tools.governance_tool_executor import GovernanceToolExecutor
from app.core.tools.tool_exceptions import ToolNotFoundError
from app.core.tools.tool_loader import get_tool_definition, list_enabled_tools


def list_tools() -> list[ToolDefinition]:
    """Return enabled governance tool definitions."""
    return list_enabled_tools()


def call_tool(request: ToolCallRequest) -> ToolCallResponse:
    """Execute one governance tool through the shared local executor."""
    executor = GovernanceToolExecutor()
    try:
        tool_definition = get_tool_definition(request.tool_name)
    except ToolNotFoundError as exc:
        return executor.build_unavailable_tool_response(
            request.tool_name,
            request.arguments,
            str(exc),
        )

    if not tool_definition.enabled:
        return executor.build_unavailable_tool_response(
            request.tool_name,
            request.arguments,
            f"Tool '{request.tool_name}' is currently disabled.",
        )

    return executor.call_registered_tool(tool_definition, request.arguments)


# TODO: add adapter-specific request normalization when external tool runtimes are introduced.
