"""Tool console page for direct local tool execution and trace inspection."""

import json
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_agent_shell_session_id, ensure_project_root_on_path
from app.ui.page_utils import (
    get_latest_tool_call_response,
    get_uploaded_file_path,
    get_workflow_result,
    initialize_session_state,
    set_latest_tool_call_response,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.audit.trace_store import get_trace, list_recent_traces
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.ui.status_blocks import render_key_value_block, render_page_header
from app.core.models.workflow_result import WorkflowResult
from app.core.tools.tool_service import call_tool
from app.core.models.tool_call_request import ToolCallRequest
from app.ui.performance_helpers import render_json_section
from app.ui.workbench_cache import (
    build_tool_console_default_arguments,
    list_tools_cached,
    tool_registry_cache_key,
)

initialize_session_state()

render_page_header(
    "Tool Console",
    (
        "Call the local governance tool layer directly, inspect normalized tool responses, "
        "and review recent execution traces."
    ),
)

uploaded_file_path = get_uploaded_file_path()
session_id = ensure_agent_shell_session_id()
tool_definitions = list_tools_cached(tool_registry_cache_key())
tool_lookup = {tool.name: tool for tool in tool_definitions}
tool_names = list(tool_lookup.keys())

default_arguments = build_tool_console_default_arguments(
    uploaded_file_path,
    get_workflow_result(),
    session_id,
)


def _store_tool_workflow_result(selected_tool_name: str, result: object) -> None:
    if result is None or not isinstance(result, dict):
        return

    result_payload = result.get("result")
    if result_payload is None and selected_tool_name == "build_execution_ready_package":
        current_result = get_workflow_result()
        if isinstance(current_result, WorkflowResult):
            package_payload = result.get("execution_ready_package")
            summary_payload = result.get("execution_package_summary")
            if isinstance(package_payload, dict):
                current_result.execution_ready_package = (
                    ExecutionReadyPackage.model_validate(package_payload)
                )
            if isinstance(summary_payload, dict):
                current_result.execution_package_summary = summary_payload
            set_workflow_result_state(current_result)
        return

    if isinstance(result_payload, dict):
        set_workflow_result_state(WorkflowResult.model_validate(result_payload))

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
    default_arguments.get(selected_tool_name, {}),
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
        set_latest_tool_call_response(tool_response)
        if selected_tool_name in {
            "run_governance_profile",
            "recommend_quality_rules",
            "recommend_quality_intelligence",
            "build_execution_ready_package",
        }:
            _store_tool_workflow_result(selected_tool_name, tool_response.result)
        st.success("Tool call completed.")

tool_response = get_latest_tool_call_response()
if tool_response is not None:
    render_key_value_block(
        "Tool Response",
        summary=tool_response.message,
        rows=[
            ("Tool", tool_response.tool_name),
            ("Status", tool_response.status),
            ("Trace ID", tool_response.trace_id or "N/A"),
        ],
    )
    if tool_response.result is not None:
        render_json_section("Tool Response Payload", tool_response.result, compact=True)

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
        render_key_value_block(
            None,
            summary=selected_trace.message,
            rows=[
                ("Tool", selected_trace.tool_name),
                ("Status", selected_trace.status),
                ("Session ID", selected_trace.session_id or "N/A"),
                ("Profile", selected_trace.profile_name or "N/A"),
                ("Stages", ", ".join(selected_trace.stages_executed) or "N/A"),
            ],
        )
        render_json_section("Trace Details", selected_trace)
