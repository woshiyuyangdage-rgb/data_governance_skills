"""Helpers for API routes that proxy local tool calls."""

from collections.abc import Collection

from fastapi import HTTPException

from app.core.models.tool_call_request import ToolCallRequest
from app.core.models.tool_call_response import ToolCallResponse
from app.core.tools.tool_service import call_tool


def call_tool_or_400(
    tool_name: str,
    arguments: dict[str, object],
    success_statuses: Collection[str] = ("success",),
) -> ToolCallResponse:
    """Call one local tool and translate failed statuses into HTTP 400."""
    response = call_tool(ToolCallRequest(tool_name=tool_name, arguments=arguments))
    if response.status not in success_statuses:
        raise HTTPException(status_code=400, detail=response.message)
    return response


def expand_tool_response(response: ToolCallResponse) -> dict[str, object]:
    """Return a tool response with its result fields expanded."""
    return {
        "message": response.message,
        "trace_id": response.trace_id,
        **(response.result or {}),
    }


def wrap_tool_response(
    response: ToolCallResponse,
    result_key: str = "result",
) -> dict[str, object]:
    """Return a tool response with the result under a named key."""
    return {
        "message": response.message,
        "trace_id": response.trace_id,
        result_key: response.result,
    }


def call_tool_and_expand(
    tool_name: str,
    arguments: dict[str, object],
    success_statuses: Collection[str] = ("success",),
) -> dict[str, object]:
    """Call one local tool and expand the response result fields."""
    return expand_tool_response(
        call_tool_or_400(tool_name, arguments, success_statuses=success_statuses)
    )


def call_tool_and_wrap(
    tool_name: str,
    arguments: dict[str, object],
    result_key: str = "result",
    success_statuses: Collection[str] = ("success",),
) -> dict[str, object]:
    """Call one local tool and wrap the response result under a named key."""
    return wrap_tool_response(
        call_tool_or_400(tool_name, arguments, success_statuses=success_statuses),
        result_key=result_key,
    )
