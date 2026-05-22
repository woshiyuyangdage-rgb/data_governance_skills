"""Adapter console for capability manifest, schema export, and local invocation."""

import json
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_latest_adapter_invocation_result,
    get_uploaded_file_path,
    get_workflow_result,
    initialize_session_state,
    set_latest_adapter_invocation_result,
)

ensure_project_root_on_path()

from app.core.adapters.invocation_adapter import InvocationAdapter
from app.ui.performance_helpers import records_to_dataframe, render_json_section
from app.ui.status_blocks import render_key_value_block, render_metric_row, render_page_header
from app.ui.workbench_cache import (
    adapter_schema_cache_key,
    adapter_schema_bundle_cached,
    build_adapter_console_default_arguments,
)

initialize_session_state()

adapter = InvocationAdapter()
schema_cache_key = adapter_schema_cache_key()
schema_bundle = adapter_schema_bundle_cached(schema_cache_key)
manifest = schema_bundle["manifest"]
native_schemas = schema_bundle["native_schemas"]
openai_schemas = schema_bundle["openai_schemas"]
mcp_manifest = schema_bundle["mcp_manifest"]

native_schema_lookup = {schema.tool_name: schema for schema in native_schemas}
tool_names = list(native_schema_lookup.keys())

default_arguments = build_adapter_console_default_arguments(
    get_uploaded_file_path(),
    get_workflow_result(),
)

render_page_header(
    "Adapter Console",
    (
        "Inspect adapter-ready capability exports and invoke the local tool platform "
        "through native or OpenAI-style adapter shapes."
    ),
)

st.subheader("Capability Manifest")
render_metric_row(
    [
        ("Service", manifest.service_name),
        ("Version", manifest.version),
        ("Tool Count", len(manifest.tools)),
    ],
)
st.caption(manifest.description)

with st.expander("Capability Manifest JSON", expanded=False):
    render_json_section("Capability Manifest JSON", manifest, compact=True)

tab_native, tab_openai, tab_mcp = st.tabs(
    ["Native Schemas", "OpenAI-Style Schemas", "MCP-Style Manifest"]
)

with tab_native:
    render_json_section(
        "Native Schemas",
        records_to_dataframe(native_schemas).to_dict("records"),
        compact=True,
    )

with tab_openai:
    render_json_section("OpenAI-Style Schemas", openai_schemas, compact=True)

with tab_mcp:
    render_json_section("MCP-Style Manifest", mcp_manifest, compact=True)

st.subheader("Local Adapter Invocation")
adapter_mode = st.selectbox(
    "Adapter Mode",
    options=["native", "openai_style", "manifest"],
)
selected_tool_name = st.selectbox("Tool", options=tool_names)
selected_schema = native_schema_lookup[selected_tool_name]
st.caption(
    f"Category: {selected_schema.category or 'unknown'} | "
    f"Description: {selected_schema.description}"
)

default_arguments_json = json.dumps(
    default_arguments.get(selected_tool_name, {}),
    ensure_ascii=False,
    indent=2,
)
arguments_text = st.text_area(
    "Arguments",
    value=default_arguments_json,
    height=220,
    key=f"adapter_console_arguments_{adapter_mode}_{selected_tool_name}",
)

if st.button("Invoke Through Adapter", type="primary"):
    try:
        parsed_arguments = json.loads(arguments_text or "{}")
        if not isinstance(parsed_arguments, dict):
            raise ValueError("Arguments must be a JSON object.")
        if adapter_mode == "native":
            result = adapter.invoke_native_tool(selected_tool_name, parsed_arguments)
        elif adapter_mode == "openai_style":
            result = adapter.invoke_openai_style(selected_tool_name, arguments_text)
        else:
            result = adapter.invoke_manifest_tool(selected_tool_name, parsed_arguments)
    except Exception as exc:
        st.error(f"Adapter invocation failed: {exc}")
    else:
        set_latest_adapter_invocation_result(result)
        if result.status in {"success", "executed_successfully", "interpreted_only"}:
            st.success("Adapter invocation completed.")
        else:
            st.error(result.message)

result = get_latest_adapter_invocation_result()
if result is not None:
    render_key_value_block(
        "Invocation Result",
        summary=result.message,
        rows=[
            ("Adapter", result.adapter_name),
            ("Tool", result.tool_name),
            ("Status", result.status),
            ("Trace ID", result.trace_id or "N/A"),
        ],
    )
    if result.tool_response is not None:
        render_json_section("Tool Response", result.tool_response, compact=True)
