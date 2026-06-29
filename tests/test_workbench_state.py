"""Tests for Streamlit workbench state restoration."""

from app.core.models.tool_call_response import ToolCallResponse
from app.ui import session_keys as keys
from app.ui.workbench_state import WorkbenchState


class _FakeSession:
    session_id = "session-1"
    last_uploaded_file_path = "sample.csv"
    last_task_request = None
    last_task_response = None
    last_tool_response = ToolCallResponse(
        tool_name="learning_health",
        status="success",
        message="ok",
        result={"total_memory_count": 3},
        trace_id="trace-1",
    )
    last_exported_files = {"report": "report.json"}


def test_restore_agent_session_to_state_restores_tool_response() -> None:
    state = WorkbenchState(session_state={})

    state.restore_agent_session_to_state(_FakeSession(), source_label="snapshot.json")

    assert state.get_agent_shell_session_id() == "session-1"
    assert state.get_restored_session_id() == "session-1"
    assert state.get_restored_session_source() == "snapshot.json"
    assert state.session_state[keys.LATEST_TOOL_CALL_RESPONSE] is not None
    assert state.session_state[keys.LATEST_TOOL_CALL_RESPONSE].tool_name == "learning_health"
    assert state.get_latest_report_paths() == {"report": "report.json"}
