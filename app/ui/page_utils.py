"""Shared helpers for Streamlit pages."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_TEMPLATE_DOC_PATH = PROJECT_ROOT / "docs" / "input_template_spec.md"
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"
UPLOAD_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "uploads"
REPORT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"
OVERRIDE_OUTPUT_DIR = PROJECT_ROOT / "app" / "data" / "overrides"
REVIEW_HISTORY_OUTPUT_DIR = PROJECT_ROOT / "app" / "data" / "review_history"
CONTROL_PLANE_DIR = PROJECT_ROOT / "app" / "data" / "control_plane"


def ensure_project_root_on_path() -> None:
    """Make project imports work when Streamlit runs page files directly."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


def initialize_session_state() -> None:
    """Register common session keys used across the workbench pages."""
    defaults = {
        "uploaded_file_path": None,
        "uploaded_file_name": None,
        "uploaded_file_size": None,
        "uploaded_file_extension": None,
        "uploaded_file_signature": None,
        "selected_workflow_profile": "metadata_diagnosis_only",
        "workflow_result": None,
        "workflow_result_file_path": None,
        "governance_task_response": None,
        "latest_intent_execution_result": None,
        "latest_agent_shell_result": None,
        "latest_tool_call_response": None,
        "latest_adapter_invocation_result": None,
        "latest_control_plane_result": None,
        "latest_execution_ready_package": None,
        "latest_execution_package_export_results": [],
        "agent_shell_session_id": None,
        "latest_review_summary": None,
        "latest_report_paths": {},
        "report_export_history": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def ensure_agent_shell_session_id() -> str:
    """Return one reusable local agent shell session id for Streamlit pages."""
    session_id = st.session_state.get("agent_shell_session_id")

    from app.core.agent.session_store import create_session, get_session

    if session_id:
        existing = get_session(session_id)
        if existing is not None:
            return existing.session_id
        recreated = create_session(session_id)
        st.session_state["agent_shell_session_id"] = recreated.session_id
        return recreated.session_id

    created = create_session()
    st.session_state["agent_shell_session_id"] = created.session_id
    return created.session_id
