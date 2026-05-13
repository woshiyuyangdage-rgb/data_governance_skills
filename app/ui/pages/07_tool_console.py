"""Tool console page for direct local tool execution and trace inspection."""

import json
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_agent_shell_session_id, ensure_project_root_on_path
from app.ui.page_utils import initialize_session_state

ensure_project_root_on_path()

from app.core.audit.trace_store import get_trace, list_recent_traces
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.workflow_result import WorkflowResult
from app.core.tools.tool_service import call_tool, list_tools
from app.core.models.tool_call_request import ToolCallRequest

initialize_session_state()

st.title("Tool Console")
st.write(
    "Call the local governance tool layer directly, inspect normalized tool responses, "
    "and review recent execution traces."
)

uploaded_file_path = st.session_state.get("uploaded_file_path")
session_id = ensure_agent_shell_session_id()
tool_definitions = list_tools()
tool_lookup = {tool.name: tool for tool in tool_definitions}
tool_names = list(tool_lookup.keys())

DEFAULT_ARGUMENTS = {
    "run_governance_profile": {
        "file_path": uploaded_file_path or "",
        "profile_name": "metadata_diagnosis_only",
        "export_reports": False,
        "apply_review_replay": False,
    },
    "recommend_quality_rules": {
        "file_path": uploaded_file_path or "",
        "profile_name": "diagnosis_mapping_stg_quality",
        "export_reports": False,
        "apply_review_replay": False,
    },
    "recommend_quality_intelligence": {
        "file_path": uploaded_file_path or "",
        "profile_name": "diagnosis_mapping_stg_quality",
        "export_reports": False,
        "apply_review_replay": False,
    },
    "review_quality_rules": {
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "review_inputs": {},
        "save_overrides": False,
    },
    "batch_review_quality_rules": {
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "action": "mark_low_confidence_manual_review",
        "confidence_threshold": 0.4,
        "save_overrides": False,
    },
    "export_confirmed_quality_rules": {
        "export_format": "json",
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "output_dir": str(PROJECT_ROOT / "outputs" / "rule_exports"),
        "base_filename": "tool_console_quality_rules",
        "apply_review_replay": True,
    },
    "build_execution_ready_package": {
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "file_path": uploaded_file_path or "",
        "apply_review_replay": True,
        "profile_name": "diagnosis_mapping_stg_quality_package_with_review",
    },
    "export_execution_ready_package": {
        "export_format": "manifest",
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "file_path": uploaded_file_path or "",
        "output_dir": str(PROJECT_ROOT / "outputs" / "execution_packages"),
        "base_filename": "tool_console_execution_package",
        "apply_review_replay": True,
    },
    "assess_governance_readiness": {
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "file_path": uploaded_file_path or "",
        "apply_review_replay": True,
    },
    "build_governance_work_package": {
        "workflow_result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else {}
        ),
        "file_path": uploaded_file_path or "",
        "export_package": True,
        "output_dir": str(PROJECT_ROOT / "outputs" / "governance_work_packages"),
        "base_filename": "tool_console_governance_work_package",
        "apply_review_replay": True,
    },
    "interpret_governance_intent": {
        "text": "Run standard mapping and export reports",
        "file_path": uploaded_file_path or "",
    },
    "preview_agent_plan": {
        "text": "Help me inspect this file",
        "file_path": "",
        "session_id": session_id,
    },
    "run_agent_task": {
        "text": "Help me inspect this file",
        "file_path": "",
        "session_id": session_id,
        "force_run": False,
    },
    "resolve_governance_context": {
        "text": "Help me inspect this file",
        "file_path": "",
        "session_id": session_id,
    },
    "export_governance_reports": {
        "profile_name": "metadata_diagnosis_only",
        "result": (
            st.session_state.get("workflow_result").model_dump()
            if hasattr(st.session_state.get("workflow_result"), "model_dump")
            else (
                st.session_state.get("workflow_result")
                if isinstance(st.session_state.get("workflow_result"), dict)
                else {}
            )
            if st.session_state.get("workflow_result") is not None
            else {}
        ),
        "output_dir": str(PROJECT_ROOT / "outputs" / "reports"),
        "base_filename": "tool_console_export",
    },
    "list_config_assets": {},
    "get_config_asset": {
        "asset_name": "workflow_profiles",
    },
    "validate_config_asset": {
        "asset_name": "workflow_profiles",
    },
    "save_config_asset": {
        "asset_name": "workflow_profiles",
        "content": (
            "profiles:\n"
            "  - name: metadata_diagnosis_only\n"
            "    enabled: true\n"
            "    description: Run metadata diagnosis only\n"
            "    stages:\n"
            "      - diagnosis\n"
            "    supports_review_replay: false\n"
            "    default_report_mode: diagnosis\n"
        ),
    },
    "publish_config_asset": {
        "asset_name": "workflow_profiles",
    },
}

selected_tool_name = st.selectbox(
    "Tool",
    options=tool_names,
    format_func=lambda name: f"{name} - {tool_lookup[name].description}",
)
selected_tool = tool_lookup[selected_tool_name]

st.caption(
    f"Category: {selected_tool.category} | input: {selected_tool.input_model} | output: {selected_tool.output_model}"
)

default_arguments_json = json.dumps(
    DEFAULT_ARGUMENTS.get(selected_tool_name, {}),
    ensure_ascii=False,
    indent=2,
)
arguments_text = st.text_area(
    "Tool Arguments (JSON)",
    value=default_arguments_json,
    height=220,
    key=f"tool_console_arguments_{selected_tool_name}",
)

if st.button("Call Tool", type="primary"):
    try:
        arguments = json.loads(arguments_text or "{}")
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        tool_response = call_tool(
            ToolCallRequest(
                tool_name=selected_tool_name,
                arguments=arguments,
            )
        )
    except Exception as exc:
        st.error(f"Failed to call tool: {exc}")
    else:
        st.session_state["latest_tool_call_response"] = tool_response
        if (
            selected_tool_name
            in {
                "run_governance_profile",
                "recommend_quality_rules",
                "recommend_quality_intelligence",
                "build_execution_ready_package",
            }
            and tool_response.result is not None
            and isinstance(tool_response.result, dict)
        ):
            result_payload = tool_response.result.get("result")
            if result_payload is None and selected_tool_name == "build_execution_ready_package":
                current_result = st.session_state.get("workflow_result")
                if isinstance(current_result, WorkflowResult):
                    package_payload = tool_response.result.get("execution_ready_package")
                    summary_payload = tool_response.result.get("execution_package_summary")
                    if isinstance(package_payload, dict):
                        current_result.execution_ready_package = (
                            ExecutionReadyPackage.model_validate(package_payload)
                        )
                    if isinstance(summary_payload, dict):
                        current_result.execution_package_summary = summary_payload
                    st.session_state["workflow_result"] = current_result
            if isinstance(result_payload, dict):
                st.session_state["workflow_result"] = WorkflowResult.model_validate(
                    result_payload
                )
        st.success("Tool call completed.")

tool_response = st.session_state.get("latest_tool_call_response")
if tool_response is not None:
    st.subheader("Tool Response")
    st.write(f"Tool: `{tool_response.tool_name}`")
    st.write(f"Status: `{tool_response.status}`")
    st.write(f"Trace ID: `{tool_response.trace_id or 'N/A'}`")
    st.caption(tool_response.message)
    if tool_response.result is not None:
        st.json(tool_response.result)

recent_traces = list_recent_traces(limit=20)
st.subheader("Recent Traces")
if not recent_traces:
    st.info("No execution traces are available yet.")
else:
    trace_options = [trace.trace_id for trace in recent_traces]
    selected_trace_id = st.selectbox(
        "Trace ID",
        options=trace_options,
        index=0,
    )
    selected_trace = get_trace(selected_trace_id)
    if selected_trace is not None:
        st.write(f"Tool: `{selected_trace.tool_name}`")
        st.write(f"Status: `{selected_trace.status}`")
        st.write(f"Session ID: `{selected_trace.session_id or 'N/A'}`")
        st.write(f"Profile: `{selected_trace.profile_name or 'N/A'}`")
        st.write(f"Stages: `{', '.join(selected_trace.stages_executed) or 'N/A'}`")
        if selected_trace.message:
            st.caption(selected_trace.message)
        st.json(selected_trace.model_dump())
