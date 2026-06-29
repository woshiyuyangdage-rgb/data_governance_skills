"""Typed wrapper around Streamlit workbench session state."""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import streamlit as st

from app.ui import session_keys as keys
from app.ui.session_keys import build_session_defaults


class WorkbenchState:
    """Convenience wrapper for the workbench's shared Streamlit state."""

    def __init__(self, session_state: MutableMapping[str, Any] | None = None) -> None:
        self.session_state = st.session_state if session_state is None else session_state

    @classmethod
    def current(
        cls,
        session_state: MutableMapping[str, Any] | None = None,
    ) -> WorkbenchState:
        return cls(session_state)

    def initialize_defaults(self) -> None:
        for key, value in build_session_defaults().items():
            self.session_state.setdefault(key, value)

    def get_value(self, key: str, default: Any | None = None) -> Any | None:
        return self.session_state.get(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self.session_state[key] = value

    def get_uploaded_file_path(self) -> str | None:
        return self.session_state.get(keys.UPLOADED_FILE_PATH)

    def get_uploaded_file_signature(self) -> str | None:
        return self.session_state.get(keys.UPLOADED_FILE_SIGNATURE)

    def get_uploaded_file_name(self) -> str | None:
        return self.session_state.get(keys.UPLOADED_FILE_NAME)

    def get_uploaded_file_size(self) -> int | None:
        return self.session_state.get(keys.UPLOADED_FILE_SIZE)

    def get_uploaded_file_extension(self) -> str | None:
        return self.session_state.get(keys.UPLOADED_FILE_EXTENSION)

    def get_current_input_file_path(self, *, prefer_workflow_result: bool = True) -> str | None:
        if prefer_workflow_result:
            workflow_file_path = self.session_state.get(keys.WORKFLOW_RESULT_FILE_PATH)
            if workflow_file_path:
                return workflow_file_path
        return self.get_uploaded_file_path()

    def get_workflow_result(self) -> Any | None:
        return self.session_state.get(keys.WORKFLOW_RESULT)

    def get_task_response(self) -> Any | None:
        return self.session_state.get(keys.GOVERNANCE_TASK_RESPONSE)

    def get_selected_workflow_profile(self, default: str | None = None) -> str | None:
        return self.session_state.get(keys.SELECTED_WORKFLOW_PROFILE, default)

    def set_selected_workflow_profile(self, profile_name: str) -> None:
        self.session_state[keys.SELECTED_WORKFLOW_PROFILE] = profile_name

    def get_latest_report_paths(self) -> dict[str, str]:
        return dict(self.session_state.get(keys.LATEST_REPORT_PATHS, {}))

    def get_report_export_history(self) -> list[dict[str, str]]:
        history = self.session_state.get(keys.REPORT_EXPORT_HISTORY, [])
        return [dict(item) for item in history]

    def set_latest_review_summary(self, review_summary: Any | None) -> None:
        self.session_state[keys.LATEST_REVIEW_SUMMARY] = review_summary

    def get_latest_review_summary(self) -> Any | None:
        return self.session_state.get(keys.LATEST_REVIEW_SUMMARY)

    def set_latest_intent_execution_result(self, execution_result: Any | None) -> None:
        self.session_state[keys.LATEST_INTENT_EXECUTION_RESULT] = execution_result

    def get_latest_intent_execution_result(self) -> Any | None:
        return self.session_state.get(keys.LATEST_INTENT_EXECUTION_RESULT)

    def set_latest_agent_shell_result(self, shell_result: Any | None) -> None:
        self.session_state[keys.LATEST_AGENT_SHELL_RESULT] = shell_result
        session_id = getattr(shell_result, "session_id", None)
        if session_id:
            self.session_state[keys.AGENT_SHELL_SESSION_ID] = session_id

    def get_latest_agent_shell_result(self) -> Any | None:
        return self.session_state.get(keys.LATEST_AGENT_SHELL_RESULT)

    def set_latest_tool_call_response(self, tool_response: Any | None) -> None:
        self.session_state[keys.LATEST_TOOL_CALL_RESPONSE] = tool_response

    def get_latest_tool_call_response(self) -> Any | None:
        return self.session_state.get(keys.LATEST_TOOL_CALL_RESPONSE)

    def set_latest_adapter_invocation_result(self, result: Any | None) -> None:
        self.session_state[keys.LATEST_ADAPTER_INVOCATION_RESULT] = result

    def get_latest_adapter_invocation_result(self) -> Any | None:
        return self.session_state.get(keys.LATEST_ADAPTER_INVOCATION_RESULT)

    def get_agent_shell_session_id(self) -> str | None:
        return self.session_state.get(keys.AGENT_SHELL_SESSION_ID)

    def get_restored_session_id(self) -> str | None:
        return self.session_state.get(keys.RESTORED_SESSION_ID)

    def get_restored_session_source(self) -> str | None:
        return self.session_state.get(keys.RESTORED_SESSION_SOURCE)

    def get_batch_file_paths(self) -> list[str]:
        return list(self.session_state.get(keys.BATCH_FILE_PATHS, []))

    def set_batch_file_paths(self, file_paths: list[str]) -> None:
        self.session_state[keys.BATCH_FILE_PATHS] = list(file_paths)

    def get_confirmation_import_file_path(self) -> str | None:
        return self.session_state.get(keys.CONFIRMATION_IMPORT_FILE_PATH)

    def set_confirmation_import_file_path(self, file_path: str | None) -> None:
        self.session_state[keys.CONFIRMATION_IMPORT_FILE_PATH] = file_path

    def get_confirmation_validation_result(self) -> Any | None:
        return self.session_state.get(keys.CONFIRMATION_VALIDATION_RESULT)

    def set_confirmation_validation_result(self, validation_result: Any | None) -> None:
        self.session_state[keys.CONFIRMATION_VALIDATION_RESULT] = validation_result

    def get_confirmation_template_diagnosis(self) -> Any | None:
        return self.session_state.get(keys.CONFIRMATION_TEMPLATE_DIAGNOSIS)

    def set_confirmation_template_diagnosis(self, diagnosis: Any | None) -> None:
        self.session_state[keys.CONFIRMATION_TEMPLATE_DIAGNOSIS] = diagnosis

    def reset_workflow_state(self, *, clear_reports: bool = True) -> None:
        self.session_state[keys.WORKFLOW_RESULT] = None
        self.session_state[keys.WORKFLOW_RESULT_FILE_PATH] = None
        self.session_state[keys.GOVERNANCE_TASK_RESPONSE] = None
        self.session_state[keys.LATEST_REVIEW_SUMMARY] = None
        self.session_state[keys.LATEST_EXECUTION_READY_PACKAGE] = None
        self.session_state[keys.LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS] = []
        if clear_reports:
            self.session_state[keys.LATEST_REPORT_PATHS] = {}

    def set_uploaded_file_state(
        self,
        *,
        file_path: str | Path,
        file_name: str | None = None,
        file_size: int | None = None,
        file_extension: str | None = None,
        file_signature: str | None = None,
        source_label: str | None = None,
        reset_workflow: bool = True,
    ) -> None:
        resolved_path = Path(file_path)
        self.session_state[keys.UPLOADED_FILE_PATH] = str(resolved_path)
        self.session_state[keys.UPLOADED_FILE_NAME] = file_name or resolved_path.name
        self.session_state[keys.UPLOADED_FILE_SIZE] = (
            file_size if file_size is not None else resolved_path.stat().st_size
        )
        self.session_state[keys.UPLOADED_FILE_EXTENSION] = (
            file_extension if file_extension is not None else resolved_path.suffix.lstrip(".")
        )
        self.session_state[keys.UPLOADED_FILE_SIGNATURE] = file_signature
        if source_label is not None:
            self.session_state[keys.RESTORED_SESSION_SOURCE] = source_label
        if reset_workflow:
            self.reset_workflow_state()

    def record_report_paths(self, report_paths: dict[str, str] | None) -> None:
        if not report_paths:
            return
        self.session_state[keys.LATEST_REPORT_PATHS] = dict(report_paths)
        history = list(self.session_state.get(keys.REPORT_EXPORT_HISTORY, []))
        history.append(dict(report_paths))
        self.session_state[keys.REPORT_EXPORT_HISTORY] = history[-10:]

    def set_workflow_result_state(
        self,
        result: Any,
        *,
        file_path: str | None = None,
        task_response: Any | None = None,
        report_paths: dict[str, str] | None = None,
    ) -> None:
        self.session_state[keys.WORKFLOW_RESULT] = result
        if file_path:
            self.session_state[keys.WORKFLOW_RESULT_FILE_PATH] = file_path
        if task_response is not None:
            self.session_state[keys.GOVERNANCE_TASK_RESPONSE] = task_response
            exported_files = getattr(task_response, "exported_files", None)
            if exported_files:
                self.record_report_paths(dict(exported_files))
        if report_paths:
            self.record_report_paths(report_paths)

    def set_task_response_state(self, task_response: Any, *, file_path: str | None = None) -> None:
        result = getattr(task_response, "result", None)
        self.set_workflow_result_state(
            result,
            file_path=file_path,
            task_response=task_response,
        )

    def ensure_agent_shell_session_id(self) -> str:
        session_id = self.get_agent_shell_session_id()

        from app.core.agent.session_store import create_session, get_session

        if session_id:
            existing = get_session(session_id)
            if existing is not None:
                return existing.session_id
            recreated = create_session(session_id)
            self.session_state[keys.AGENT_SHELL_SESSION_ID] = recreated.session_id
            return recreated.session_id

        created = create_session()
        self.session_state[keys.AGENT_SHELL_SESSION_ID] = created.session_id
        return created.session_id

    def restore_agent_session_to_state(self, session, *, source_label: str | None = None) -> None:
        self.session_state[keys.AGENT_SHELL_SESSION_ID] = session.session_id
        self.session_state[keys.RESTORED_SESSION_ID] = session.session_id
        if source_label is not None:
            self.session_state[keys.RESTORED_SESSION_SOURCE] = source_label

        if getattr(session, "last_uploaded_file_path", None):
            uploaded_file_path = Path(session.last_uploaded_file_path)
            self.session_state[keys.UPLOADED_FILE_PATH] = str(uploaded_file_path)
            self.session_state[keys.UPLOADED_FILE_NAME] = uploaded_file_path.name
            if uploaded_file_path.exists():
                self.session_state[keys.UPLOADED_FILE_SIZE] = uploaded_file_path.stat().st_size
                self.session_state[keys.UPLOADED_FILE_EXTENSION] = (
                    uploaded_file_path.suffix.lstrip(".")
                )

        if getattr(session, "last_task_request", None) is not None:
            task_request = session.last_task_request
            if getattr(task_request, "file_path", None):
                self.session_state[keys.WORKFLOW_RESULT_FILE_PATH] = task_request.file_path

        if (
            not self.session_state.get(keys.WORKFLOW_RESULT_FILE_PATH)
            and self.session_state.get(keys.UPLOADED_FILE_PATH)
        ):
            self.session_state[keys.WORKFLOW_RESULT_FILE_PATH] = self.session_state[
                keys.UPLOADED_FILE_PATH
            ]

        if getattr(session, "last_task_response", None) is not None:
            task_response = session.last_task_response
            self.session_state[keys.WORKFLOW_RESULT] = task_response.result
            if getattr(task_response, "exported_files", None):
                self.session_state[keys.LATEST_REPORT_PATHS] = dict(task_response.exported_files)

        if getattr(session, "last_tool_response", None) is not None:
            self.session_state[keys.LATEST_TOOL_CALL_RESPONSE] = session.last_tool_response

        if getattr(session, "last_exported_files", None):
            self.session_state[keys.LATEST_REPORT_PATHS] = dict(session.last_exported_files)

    def set_latest_control_plane_preview(self, preview: str | None) -> None:
        self.session_state[keys.LATEST_CONTROL_PLANE_PREVIEW] = preview

    def get_latest_control_plane_preview(self) -> str | None:
        return self.session_state.get(keys.LATEST_CONTROL_PLANE_PREVIEW)

    def set_latest_control_plane_result(self, result: Any | None) -> None:
        self.session_state[keys.LATEST_CONTROL_PLANE_RESULT] = result

    def get_latest_control_plane_result(self) -> Any | None:
        return self.session_state.get(keys.LATEST_CONTROL_PLANE_RESULT)

    def set_latest_execution_ready_package(self, package: Any | None) -> None:
        self.session_state[keys.LATEST_EXECUTION_READY_PACKAGE] = package

    def get_latest_execution_ready_package(self) -> Any | None:
        return self.session_state.get(keys.LATEST_EXECUTION_READY_PACKAGE)

    def set_latest_execution_package_export_results(self, results: list[Any] | None) -> None:
        self.session_state[keys.LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS] = list(results or [])

    def get_latest_execution_package_export_results(self) -> list[Any]:
        results = self.session_state.get(keys.LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS, [])
        return [dict(item) if isinstance(item, dict) else item for item in results]
