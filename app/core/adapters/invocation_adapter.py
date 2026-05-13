"""Local adapter wrappers for alternate tool invocation shapes."""

import json

from app.core.adapters.adapter_loader import load_adapter_config
from app.core.models.adapter_invocation_result import AdapterInvocationResult
from app.core.models.tool_call_request import ToolCallRequest
from app.core.tools.tool_service import call_tool


class InvocationAdapter:
    """Forward adapter-shaped calls, including delivery tools, into the local tool layer."""

    def __init__(self) -> None:
        self.config = load_adapter_config()

    def _build_result(
        self,
        adapter_name: str,
        tool_name: str,
        tool_response=None,
        status: str = "failed",
        message: str = "",
    ) -> AdapterInvocationResult:
        return AdapterInvocationResult(
            adapter_name=adapter_name,
            tool_name=tool_name,
            status=(tool_response.status if tool_response is not None else status),
            message=(tool_response.message if tool_response is not None else message),
            tool_response=(tool_response.model_dump() if tool_response is not None else None),
            trace_id=(tool_response.trace_id if tool_response is not None else None),
        )

    def invoke_native_tool(
        self,
        tool_name: str,
        arguments: dict[str, object] | None = None,
    ) -> AdapterInvocationResult:
        """Invoke one registered tool through the native local adapter shape."""
        tool_response = call_tool(
            ToolCallRequest(
                tool_name=tool_name,
                arguments=dict(arguments or {}),
            )
        )
        return self._build_result("native", tool_name, tool_response=tool_response)

    def invoke_openai_style(
        self,
        function_name: str,
        arguments_json: str | dict[str, object] | None,
    ) -> AdapterInvocationResult:
        """Invoke one tool through a simplified OpenAI-style function payload."""
        try:
            if arguments_json is None:
                arguments: dict[str, object] = {}
            elif isinstance(arguments_json, str):
                loaded = json.loads(arguments_json) if arguments_json.strip() else {}
                if not isinstance(loaded, dict):
                    raise ValueError("OpenAI-style arguments_json must decode to an object.")
                arguments = loaded
            elif isinstance(arguments_json, dict):
                arguments = dict(arguments_json)
            else:
                raise ValueError(
                    "OpenAI-style arguments_json must be a JSON string or object."
                )
        except Exception as exc:
            return self._build_result(
                "openai_style",
                function_name,
                status="failed",
                message=f"Failed to parse OpenAI-style arguments: {exc}",
            )

        tool_response = call_tool(
            ToolCallRequest(
                tool_name=function_name,
                arguments=arguments,
            )
        )
        return self._build_result(
            "openai_style",
            function_name,
            tool_response=tool_response,
        )

    def invoke_manifest_tool(
        self,
        tool_name: str,
        arguments: dict[str, object] | None = None,
    ) -> AdapterInvocationResult:
        """Invoke one tool through the lightweight manifest-oriented adapter shape."""
        tool_response = call_tool(
            ToolCallRequest(
                tool_name=tool_name,
                arguments=dict(arguments or {}),
            )
        )
        return self._build_result("manifest", tool_name, tool_response=tool_response)


# TODO: add remote gateway and protocol-specific transport bindings only after the local adapter contract stays stable.
