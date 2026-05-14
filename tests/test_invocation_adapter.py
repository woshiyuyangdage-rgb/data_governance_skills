"""Tests for adapter-layer local invocation wrappers."""

from pathlib import Path

from app.core.adapters.invocation_adapter import InvocationAdapter
from app.core.agent import session_store
from app.core.audit import trace_store

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def _patch_runtime_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()


def test_invocation_adapter_can_invoke_native_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    adapter = InvocationAdapter()

    result = adapter.invoke_native_tool(
        "run_governance_profile",
        {
            "file_path": str(SAMPLE_METADATA_PATH),
            "profile_name": "metadata_diagnosis_only",
        },
    )

    assert result.status == "success"
    assert result.trace_id is not None


def test_invocation_adapter_can_invoke_openai_style_tool(
    tmp_path: Path,
    monkeypatch,
    isolated_control_plane_runtime: Path,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    adapter = InvocationAdapter()

    result = adapter.invoke_openai_style(
        "validate_config_asset",
        '{"asset_name": "workflow_profiles"}',
    )

    assert result.status == "success"
    assert result.trace_id is not None


def test_invocation_adapter_can_invoke_manifest_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    adapter = InvocationAdapter()

    result = adapter.invoke_manifest_tool("list_config_assets", {})

    assert result.status == "success"
    assert result.trace_id is not None


def test_invocation_adapter_can_invoke_delivery_template_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    adapter = InvocationAdapter()

    result = adapter.invoke_manifest_tool("list_delivery_template_profiles", {})

    assert result.status == "success"
    assert result.trace_id is not None
    assert result.tool_response is not None
    assert "profiles" in result.tool_response["result"]
