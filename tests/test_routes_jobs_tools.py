"""Agent shell, tool, trace, and adapter route tests."""

from pathlib import Path

from app.api.routes_jobs import (
    AgentShellPlanRequest,
    AgentShellRunRequest,
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
    agent_shell_plan,
    agent_shell_resolve_context,
    agent_shell_run,
    agent_shell_session,
    capability_manifest_route,
    call_tool_route,
    get_trace_route,
    invoke_native_tool_route,
    invoke_openai_tool_route,
    list_recent_traces_route,
    list_tools_route,
    mcp_tool_manifest_route,
    native_tool_schemas_route,
    openai_tool_schemas_route,
)
from app.core.agent import session_store
from app.core.audit import trace_store
from app.core.models.tool_call_request import ToolCallRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_list_tools_route_returns_enabled_tools() -> None:
    tools = list_tools_route()

    assert tools
    assert any(tool.name == "run_governance_profile" for tool in tools)
    assert any(tool.name == "list_config_assets" for tool in tools)
    assert any(tool.name == "recommend_quality_rules" for tool in tools)
    assert any(tool.name == "recommend_quality_intelligence" for tool in tools)
    assert any(tool.name == "review_quality_rules" for tool in tools)
    assert any(tool.name == "batch_review_quality_rules" for tool in tools)
    assert any(tool.name == "export_confirmed_quality_rules" for tool in tools)
    assert any(tool.name == "build_execution_ready_package" for tool in tools)
    assert any(tool.name == "export_execution_ready_package" for tool in tools)
    assert any(tool.name == "assess_text_to_sql_readiness" for tool in tools)
    assert any(tool.name == "assess_governance_readiness" for tool in tools)
    assert any(tool.name == "build_governance_work_package" for tool in tools)
    assert any(tool.name == "build_governance_backlog" for tool in tools)
    assert any(tool.name == "update_governance_backlog_status" for tool in tools)
    assert any(tool.name == "list_governance_backlog_items" for tool in tools)
    assert any(tool.name == "assess_governance_portfolio" for tool in tools)
    assert any(tool.name == "generate_progress_snapshot" for tool in tools)
    assert any(tool.name == "list_governance_progress_snapshots" for tool in tools)


def test_agent_shell_plan_returns_preview_result() -> None:
    response = agent_shell_plan(
        AgentShellPlanRequest(
            text="Generate STG structure suggestions",
            file_path=str(SAMPLE_METADATA_PATH),
        )
    )

    assert response.execution_plan.profile_name == "diagnosis_mapping_stg"
    assert response.task_response is None


def test_agent_shell_resolve_context_returns_resolved_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))

    response = agent_shell_resolve_context(
        AgentShellPlanRequest(
            text="Help me inspect this file",
            session_id=session.session_id,
        )
    )

    assert response.resolved_context is not None
    assert response.task_request.file_path == str(SAMPLE_METADATA_PATH)
    assert response.execution_plan.validation_passed is True


def test_agent_shell_run_can_execute_and_expose_session() -> None:
    response = agent_shell_run(
        AgentShellRunRequest(
            text="Help me inspect this file",
            file_path=str(SAMPLE_METADATA_PATH),
        )
    )

    assert response.status == "executed_successfully"
    assert response.task_response is not None
    assert response.session_id is not None

    session = agent_shell_session(response.session_id)
    assert session is not None
    assert session.last_task_response is not None


def test_call_tool_route_returns_traceable_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    response = call_tool_route(
        ToolCallRequest(
            tool_name="run_governance_profile",
            arguments={
                "file_path": str(SAMPLE_METADATA_PATH),
                "profile_name": "metadata_diagnosis_only",
            },
        )
    )

    assert response.status == "success"
    assert response.trace_id is not None

    trace = get_trace_route(response.trace_id)
    assert trace is not None
    assert trace.tool_name == "run_governance_profile"

    recent = list_recent_traces_route(limit=10)
    assert any(item.trace_id == response.trace_id for item in recent)


def test_adapter_manifest_routes_return_expected_payloads() -> None:
    manifest = capability_manifest_route()
    native_schemas = native_tool_schemas_route()
    openai_schemas = openai_tool_schemas_route()
    mcp_manifest = mcp_tool_manifest_route()

    assert manifest.service_name == "data_governance_skills"
    assert native_schemas
    assert openai_schemas
    assert "tools" in mcp_manifest


def test_adapter_invoke_routes_return_traceable_results(
    tmp_path: Path,
    monkeypatch,
    isolated_control_plane_runtime: Path,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    native_result = invoke_native_tool_route(
        NativeToolInvokeRequest(
            tool_name="run_governance_profile",
            arguments={
                "file_path": str(SAMPLE_METADATA_PATH),
                "profile_name": "metadata_diagnosis_only",
            },
        )
    )
    openai_result = invoke_openai_tool_route(
        OpenAIToolInvokeRequest(
            function_name="validate_config_asset",
            arguments_json={"asset_name": "workflow_profiles"},
        )
    )

    assert native_result.trace_id is not None
    assert native_result.status == "success"
    assert openai_result.trace_id is not None
