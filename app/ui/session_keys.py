"""Shared Streamlit session-state keys and defaults."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Union

UPLOADED_FILE_PATH = "uploaded_file_path"
UPLOADED_FILE_NAME = "uploaded_file_name"
UPLOADED_FILE_SIZE = "uploaded_file_size"
UPLOADED_FILE_EXTENSION = "uploaded_file_extension"
UPLOADED_FILE_SIGNATURE = "uploaded_file_signature"
SELECTED_WORKFLOW_PROFILE = "selected_workflow_profile"
WORKFLOW_RESULT = "workflow_result"
WORKFLOW_RESULT_FILE_PATH = "workflow_result_file_path"
GOVERNANCE_TASK_RESPONSE = "governance_task_response"
LATEST_INTENT_EXECUTION_RESULT = "latest_intent_execution_result"
LATEST_AGENT_SHELL_RESULT = "latest_agent_shell_result"
LATEST_TOOL_CALL_RESPONSE = "latest_tool_call_response"
LATEST_ADAPTER_INVOCATION_RESULT = "latest_adapter_invocation_result"
LATEST_CONTROL_PLANE_RESULT = "latest_control_plane_result"
LATEST_CONTROL_PLANE_PREVIEW = "latest_control_plane_preview"
LATEST_EXECUTION_READY_PACKAGE = "latest_execution_ready_package"
LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS = "latest_execution_package_export_results"
AGENT_SHELL_SESSION_ID = "agent_shell_session_id"
LATEST_REVIEW_SUMMARY = "latest_review_summary"
LATEST_REPORT_PATHS = "latest_report_paths"
REPORT_EXPORT_HISTORY = "report_export_history"
RESTORED_SESSION_ID = "restored_session_id"
RESTORED_SESSION_SOURCE = "restored_session_source"
BATCH_FILE_PATHS = "batch_file_paths"
CONFIRMATION_IMPORT_FILE_PATH = "confirmation_import_file_path"
CONFIRMATION_VALIDATION_RESULT = "confirmation_validation_result"
CONFIRMATION_TEMPLATE_DIAGNOSIS = "confirmation_template_diagnosis"

SessionDefault = Union[Any, Callable[[], Any]]

SESSION_DEFAULTS: dict[str, SessionDefault] = {
    UPLOADED_FILE_PATH: None,
    UPLOADED_FILE_NAME: None,
    UPLOADED_FILE_SIZE: None,
    UPLOADED_FILE_EXTENSION: None,
    UPLOADED_FILE_SIGNATURE: None,
    SELECTED_WORKFLOW_PROFILE: "metadata_diagnosis_only",
    WORKFLOW_RESULT: None,
    WORKFLOW_RESULT_FILE_PATH: None,
    GOVERNANCE_TASK_RESPONSE: None,
    LATEST_INTENT_EXECUTION_RESULT: None,
    LATEST_AGENT_SHELL_RESULT: None,
    LATEST_TOOL_CALL_RESPONSE: None,
    LATEST_ADAPTER_INVOCATION_RESULT: None,
    LATEST_CONTROL_PLANE_RESULT: None,
    LATEST_CONTROL_PLANE_PREVIEW: None,
    LATEST_EXECUTION_READY_PACKAGE: None,
    LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS: list,
    AGENT_SHELL_SESSION_ID: None,
    LATEST_REVIEW_SUMMARY: None,
    LATEST_REPORT_PATHS: dict,
    REPORT_EXPORT_HISTORY: list,
    RESTORED_SESSION_ID: None,
    RESTORED_SESSION_SOURCE: None,
    BATCH_FILE_PATHS: list,
    CONFIRMATION_IMPORT_FILE_PATH: None,
    CONFIRMATION_VALIDATION_RESULT: None,
    CONFIRMATION_TEMPLATE_DIAGNOSIS: None,
}


def build_session_defaults() -> dict[str, Any]:
    """Return fresh default values for every Streamlit session key."""
    defaults: dict[str, Any] = {}
    for key, value in SESSION_DEFAULTS.items():
        defaults[key] = value() if callable(value) else value
    return defaults
