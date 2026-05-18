"""Agent shell, tool contract, trace, and control-plane job routes."""

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    AgentShellPlanRequest,
    AgentShellRunRequest,
    ConfigAssetSaveRequest,
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
)
from app.core.adapters.invocation_adapter import InvocationAdapter
from app.core.adapters.manifest_service import (
    get_capability_manifest,
    get_mcp_style_manifest,
    get_native_tool_schemas,
    get_openai_tool_schemas,
)
from app.core.agent.agent_shell_service import AgentShellService
from app.core.agent.session_store import get_session
from app.core.audit.trace_store import get_trace, list_recent_traces
from app.core.control_plane.control_plane_service import ControlPlaneService
from app.core.models.adapter_invocation_result import AdapterInvocationResult
from app.core.models.agent_session import AgentSession
from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.capability_manifest import CapabilityManifest
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.execution_trace import ExecutionTrace
from app.core.models.exported_tool_schema import ExportedToolSchema
from app.core.models.tool_call_request import ToolCallRequest
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.tool_definition import ToolDefinition
from app.core.models.validation_result import ValidationResult
from app.core.tools.tool_service import call_tool, list_tools

router = APIRouter()
control_plane_service = ControlPlaneService()
invocation_adapter = InvocationAdapter()


@router.post("/agent-shell/plan", response_model=AgentShellResult)
def agent_shell_plan(payload: AgentShellPlanRequest) -> AgentShellResult:
    """Interpret task text and return a previewable execution plan."""
    service = AgentShellService()
    return service.interpret_to_plan(
        text=payload.text,
        file_path=payload.file_path,
        session_id=payload.session_id,
    )


@router.post("/agent-shell/resolve-context", response_model=AgentShellResult)
def agent_shell_resolve_context(payload: AgentShellPlanRequest) -> AgentShellResult:
    """Interpret task text, resolve local context, and return a previewable plan."""
    service = AgentShellService()
    return service.interpret_to_plan(
        text=payload.text,
        file_path=payload.file_path,
        session_id=payload.session_id,
    )


@router.post("/agent-shell/run", response_model=AgentShellResult)
def agent_shell_run(payload: AgentShellRunRequest) -> AgentShellResult:
    """Interpret task text, build a plan, and run it when policy allows."""
    service = AgentShellService()
    return service.confirm_and_run(
        text=payload.text,
        file_path=payload.file_path,
        session_id=payload.session_id,
        force_run=payload.force_run,
    )


@router.get("/agent-shell/session/{session_id}", response_model=AgentSession | None)
def agent_shell_session(session_id: str) -> AgentSession | None:
    """Return a local agent shell session if it exists."""
    return get_session(session_id)


@router.get("/list-tools", response_model=list[ToolDefinition])
def list_tools_route() -> list[ToolDefinition]:
    """Return enabled local governance tool definitions."""
    return list_tools()


@router.post("/call-tool", response_model=ToolCallResponse)
def call_tool_route(payload: ToolCallRequest) -> ToolCallResponse:
    """Call one governance tool through the local tool contract layer."""
    return call_tool(payload)


@router.get("/capability-manifest", response_model=CapabilityManifest)
def capability_manifest_route() -> CapabilityManifest:
    """Return the adapter-layer capability manifest."""
    return get_capability_manifest()


@router.get("/tool-schemas/native", response_model=list[ExportedToolSchema])
def native_tool_schemas_route() -> list[ExportedToolSchema]:
    """Return native adapter-layer tool schemas."""
    return get_native_tool_schemas()


@router.get("/tool-schemas/openai", response_model=list[dict[str, object]])
def openai_tool_schemas_route() -> list[dict[str, object]]:
    """Return simplified OpenAI-style function schemas."""
    return get_openai_tool_schemas()


@router.get("/tool-schemas/mcp", response_model=dict[str, object])
def mcp_tool_manifest_route() -> dict[str, object]:
    """Return a lightweight local MCP-style manifest."""
    return get_mcp_style_manifest()


@router.post("/invoke-native-tool", response_model=AdapterInvocationResult)
def invoke_native_tool_route(
    payload: NativeToolInvokeRequest,
) -> AdapterInvocationResult:
    """Invoke one local governance tool through the native adapter shape."""
    return invocation_adapter.invoke_native_tool(
        tool_name=payload.tool_name,
        arguments=payload.arguments,
    )


@router.post("/invoke-openai-tool", response_model=AdapterInvocationResult)
def invoke_openai_tool_route(
    payload: OpenAIToolInvokeRequest,
) -> AdapterInvocationResult:
    """Invoke one local governance tool through the simplified OpenAI-style shape."""
    return invocation_adapter.invoke_openai_style(
        function_name=payload.function_name,
        arguments_json=payload.arguments_json,
    )


@router.get("/trace/{trace_id}", response_model=ExecutionTrace | None)
def get_trace_route(trace_id: str) -> ExecutionTrace | None:
    """Return one saved execution trace if it exists."""
    return get_trace(trace_id)


@router.get("/traces/recent", response_model=list[ExecutionTrace])
def list_recent_traces_route(limit: int = 20) -> list[ExecutionTrace]:
    """Return recent execution traces from local audit storage."""
    return list_recent_traces(limit=limit)


@router.get("/config-assets", response_model=list[dict[str, object]])
def list_config_assets_route() -> list[dict[str, object]]:
    """Return managed control-plane assets with their current status."""
    return control_plane_service.list_assets_with_status()


@router.get("/config-assets/{asset_name}", response_model=dict[str, object])
def get_config_asset_route(asset_name: str) -> dict[str, object]:
    """Return one managed config asset with current content and status."""
    try:
        return control_plane_service.get_asset_content(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/validate",
    response_model=ValidationResult,
)
def validate_config_asset_route(asset_name: str) -> ValidationResult:
    """Validate one managed config asset."""
    try:
        return control_plane_service.validate_asset(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/save",
    response_model=ConfigEditResult,
)
def save_config_asset_route(
    asset_name: str,
    payload: ConfigAssetSaveRequest,
) -> ConfigEditResult:
    """Save one managed config asset after validation."""
    try:
        return control_plane_service.save_asset(asset_name, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/publish",
    response_model=ConfigEditResult,
)
def publish_config_asset_route(asset_name: str) -> ConfigEditResult:
    """Publish one managed config asset after validation."""
    try:
        return control_plane_service.publish_asset(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
