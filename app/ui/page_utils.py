"""Shared helpers for Streamlit pages."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import streamlit as st

from app.ui.workbench_state import WorkbenchState

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_TEMPLATE_DOC_PATH = PROJECT_ROOT / "docs" / "input_template_spec.md"
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"
UPLOAD_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "uploads"
REPORT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"
OVERRIDE_OUTPUT_DIR = PROJECT_ROOT / "app" / "data" / "overrides"
REVIEW_HISTORY_OUTPUT_DIR = PROJECT_ROOT / "app" / "data" / "review_history"
CONTROL_PLANE_DIR = PROJECT_ROOT / "app" / "data" / "control_plane"


def _state() -> WorkbenchState:
    """Return the current workbench state wrapper bound to Streamlit."""
    return WorkbenchState.current(st.session_state)


def ensure_project_root_on_path() -> None:
    """Make project imports work when Streamlit runs page files directly."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


def initialize_session_state() -> None:
    """Register common session keys used across the workbench pages."""
    _state().initialize_defaults()


def get_session_value(key: str, default: Any | None = None) -> Any | None:
    """Return a raw session value for page-local keys."""
    return _state().get_value(key, default)


def set_session_value(key: str, value: Any) -> None:
    """Store a raw session value for page-local keys."""
    _state().set_value(key, value)


def get_uploaded_file_path() -> str | None:
    """Return the active uploaded metadata file path, if any."""
    return _state().get_uploaded_file_path()


def get_uploaded_file_signature() -> str | None:
    """Return the active uploaded file signature, if any."""
    return _state().get_uploaded_file_signature()


def get_uploaded_file_name() -> str | None:
    """Return the active uploaded file name, if any."""
    return _state().get_uploaded_file_name()


def get_uploaded_file_size() -> int | None:
    """Return the active uploaded file size, if any."""
    return _state().get_uploaded_file_size()


def get_uploaded_file_extension() -> str | None:
    """Return the active uploaded file extension, if any."""
    return _state().get_uploaded_file_extension()


def get_current_input_file_path(*, prefer_workflow_result: bool = True) -> str | None:
    """Return the best available file path for pages that operate on current state."""
    return _state().get_current_input_file_path(prefer_workflow_result=prefer_workflow_result)


def get_workflow_result() -> Any | None:
    """Return the current workflow result stored in session state."""
    return _state().get_workflow_result()


def get_task_response() -> Any | None:
    """Return the current governance task response stored in session state."""
    return _state().get_task_response()


def get_selected_workflow_profile(default: str | None = None) -> str | None:
    """Return the selected workflow profile name."""
    return _state().get_selected_workflow_profile(default)


def set_selected_workflow_profile(profile_name: str) -> None:
    """Store the selected workflow profile name."""
    _state().set_selected_workflow_profile(profile_name)


def get_latest_report_paths() -> dict[str, str]:
    """Return a defensive copy of the latest exported report paths."""
    return _state().get_latest_report_paths()


def get_report_export_history() -> list[dict[str, str]]:
    """Return a defensive copy of the recent report export history."""
    return _state().get_report_export_history()


def set_latest_review_summary(review_summary: Any | None) -> None:
    """Store the latest review summary."""
    _state().set_latest_review_summary(review_summary)


def get_latest_review_summary() -> Any | None:
    """Return the latest review summary."""
    return _state().get_latest_review_summary()


def set_latest_intent_execution_result(execution_result: Any | None) -> None:
    """Store the latest intent execution result."""
    _state().set_latest_intent_execution_result(execution_result)


def get_latest_intent_execution_result() -> Any | None:
    """Return the latest intent execution result."""
    return _state().get_latest_intent_execution_result()


def set_latest_agent_shell_result(shell_result: Any | None) -> None:
    """Store the latest agent shell result and session id side effect."""
    _state().set_latest_agent_shell_result(shell_result)


def get_latest_agent_shell_result() -> Any | None:
    """Return the latest agent shell result."""
    return _state().get_latest_agent_shell_result()


def set_latest_tool_call_response(tool_response: Any | None) -> None:
    """Store the latest tool call response."""
    _state().set_latest_tool_call_response(tool_response)


def get_latest_tool_call_response() -> Any | None:
    """Return the latest tool call response."""
    return _state().get_latest_tool_call_response()


def set_latest_adapter_invocation_result(result: Any | None) -> None:
    """Store the latest adapter invocation result."""
    _state().set_latest_adapter_invocation_result(result)


def get_latest_adapter_invocation_result() -> Any | None:
    """Return the latest adapter invocation result."""
    return _state().get_latest_adapter_invocation_result()


def set_latest_control_plane_preview(preview: str | None) -> None:
    """Store the latest control-plane editor preview."""
    _state().set_latest_control_plane_preview(preview)


def get_latest_control_plane_preview() -> str | None:
    """Return the latest control-plane editor preview."""
    return _state().get_latest_control_plane_preview()


def set_latest_control_plane_result(result: Any | None) -> None:
    """Store the latest control-plane action result."""
    _state().set_latest_control_plane_result(result)


def get_latest_control_plane_result() -> Any | None:
    """Return the latest control-plane action result."""
    return _state().get_latest_control_plane_result()


def set_latest_execution_ready_package(package: Any | None) -> None:
    """Store the latest execution-ready package."""
    _state().set_latest_execution_ready_package(package)


def get_latest_execution_ready_package() -> Any | None:
    """Return the latest execution-ready package."""
    return _state().get_latest_execution_ready_package()


def set_latest_execution_package_export_results(results: list[Any] | None) -> None:
    """Store the latest execution package export results."""
    _state().set_latest_execution_package_export_results(results)


def get_latest_execution_package_export_results() -> list[Any]:
    """Return a defensive copy of latest execution package export results."""
    return _state().get_latest_execution_package_export_results()


def get_agent_shell_session_id() -> str | None:
    """Return the current agent shell session id."""
    return _state().get_agent_shell_session_id()


def get_restored_session_id() -> str | None:
    """Return the restored session id, if any."""
    return _state().get_restored_session_id()


def get_restored_session_source() -> str | None:
    """Return the restored session source, if any."""
    return _state().get_restored_session_source()


def get_batch_file_paths() -> list[str]:
    """Return saved batch input file paths."""
    return _state().get_batch_file_paths()


def set_batch_file_paths(file_paths: list[str]) -> None:
    """Store saved batch input file paths."""
    _state().set_batch_file_paths(file_paths)


def get_confirmation_import_file_path() -> str | None:
    """Return the saved confirmation workbook path."""
    return _state().get_confirmation_import_file_path()


def set_confirmation_import_file_path(file_path: str | None) -> None:
    """Store the confirmation workbook path."""
    _state().set_confirmation_import_file_path(file_path)


def get_confirmation_validation_result() -> Any | None:
    """Return the cached confirmation validation result."""
    return _state().get_confirmation_validation_result()


def set_confirmation_validation_result(validation_result: Any | None) -> None:
    """Store the cached confirmation validation result."""
    _state().set_confirmation_validation_result(validation_result)


def get_confirmation_template_diagnosis() -> Any | None:
    """Return the cached confirmation template diagnosis."""
    return _state().get_confirmation_template_diagnosis()


def set_confirmation_template_diagnosis(diagnosis: Any | None) -> None:
    """Store the cached confirmation template diagnosis."""
    _state().set_confirmation_template_diagnosis(diagnosis)


def reset_workflow_state(*, clear_reports: bool = True) -> None:
    """Clear workflow-derived state after switching the active input file."""
    _state().reset_workflow_state(clear_reports=clear_reports)


def set_uploaded_file_state(
    *,
    file_path: str | Path,
    file_name: str | None = None,
    file_size: int | None = None,
    file_extension: str | None = None,
    file_signature: str | None = None,
    source_label: str | None = None,
    reset_workflow: bool = True,
) -> None:
    """Store the active uploaded file metadata in one place."""
    _state().set_uploaded_file_state(
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        file_extension=file_extension,
        file_signature=file_signature,
        source_label=source_label,
        reset_workflow=reset_workflow,
    )


def record_report_paths(report_paths: dict[str, str] | None) -> None:
    """Store latest exported files and keep a short export history."""
    _state().record_report_paths(report_paths)


def set_workflow_result_state(
    result: Any,
    *,
    file_path: str | None = None,
    task_response: Any | None = None,
    report_paths: dict[str, str] | None = None,
) -> None:
    """Store workflow result state consistently across pages."""
    _state().set_workflow_result_state(
        result,
        file_path=file_path,
        task_response=task_response,
        report_paths=report_paths,
    )


def set_task_response_state(task_response: Any, *, file_path: str | None = None) -> None:
    """Store a governance task response and its result/export side effects."""
    _state().set_task_response_state(task_response, file_path=file_path)


def ensure_agent_shell_session_id() -> str:
    """Return one reusable local agent shell session id for Streamlit pages."""
    return _state().ensure_agent_shell_session_id()


def restore_agent_session_to_state(session, *, source_label: str | None = None) -> None:
    """Copy one persisted agent session back into Streamlit state."""
    _state().restore_agent_session_to_state(session, source_label=source_label)
