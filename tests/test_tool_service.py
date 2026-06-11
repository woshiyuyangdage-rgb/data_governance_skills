"""Tests for the local governance tool service."""

from pathlib import Path

from app.core.agent import session_store
from app.core.audit import trace_store
from app.core.models.tool_call_request import ToolCallRequest
from app.core.models.tool_definition import ToolDefinition
from app.core.tools import tool_service

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def _patch_runtime_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()


def test_tool_service_can_list_tools() -> None:
    tools = tool_service.list_tools()

    assert tools
    assert any(tool.name == "run_governance_profile" for tool in tools)
    assert any(tool.name == "list_config_assets" for tool in tools)
    assert any(tool.name == "recommend_quality_rules" for tool in tools)
    assert any(tool.name == "build_governance_backlog" for tool in tools)
    assert any(tool.name == "update_governance_backlog_status" for tool in tools)
    assert any(tool.name == "list_governance_backlog_items" for tool in tools)
    assert any(tool.name == "assess_governance_portfolio" for tool in tools)
    assert any(tool.name == "generate_progress_snapshot" for tool in tools)
    assert any(tool.name == "list_governance_progress_snapshots" for tool in tools)
    assert any(tool.name == "learning_health" for tool in tools)
    assert any(tool.name == "rebuild_review_learning" for tool in tools)


def test_tool_service_can_call_enabled_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    response = tool_service.call_tool(
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


def test_tool_service_can_call_control_plane_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    response = tool_service.call_tool(
        ToolCallRequest(
            tool_name="list_config_assets",
            arguments={},
        )
    )

    assert response.status == "success"
    assert response.trace_id is not None
    assert isinstance(response.result, list)


def test_tool_service_returns_clear_failure_for_missing_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    response = tool_service.call_tool(
        ToolCallRequest(tool_name="missing_tool", arguments={})
    )

    assert response.status == "failed"
    assert response.trace_id is not None
    assert "not found" in response.message.lower()


def test_tool_service_returns_clear_failure_for_disabled_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        tool_service,
        "get_tool_definition",
        lambda tool_name: ToolDefinition(
            name=tool_name,
            enabled=False,
            description="disabled",
            input_model="dict",
            output_model="dict",
            handler="governance_tool_executor.preview_agent_plan",
            category="test",
        ),
    )

    response = tool_service.call_tool(
        ToolCallRequest(tool_name="preview_agent_plan", arguments={"text": "demo"})
    )

    assert response.status == "failed"
    assert response.trace_id is not None
    assert "disabled" in response.message.lower()
