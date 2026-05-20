"""Adapter console for capability manifest, schema export, and local invocation."""

import json
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.adapters.invocation_adapter import InvocationAdapter
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
    st.session_state.get("uploaded_file_path"),
    st.session_state.get("workflow_result"),
)

st.title("Adapter Console")
st.write(
    "Inspect adapter-ready capability exports and invoke the local tool platform "
    "through native or OpenAI-style adapter shapes."
)

st.subheader("Capability Manifest")
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Service", manifest.service_name)
metric_col2.metric("Version", manifest.version)
metric_col3.metric("Tool Count", len(manifest.tools))
st.caption(manifest.description)

with st.expander("Capability Manifest JSON", expanded=False):
    st.json(manifest.model_dump())

tab_native, tab_openai, tab_mcp = st.tabs(
    ["Native Schemas", "OpenAI-Style Schemas", "MCP-Style Manifest"]
)

with tab_native:
    st.json([schema.model_dump() for schema in native_schemas])

with tab_openai:
    st.json(openai_schemas)

with tab_mcp:
    st.json(mcp_manifest)

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
        st.session_state["latest_adapter_invocation_result"] = result
        if result.status in {"success", "executed_successfully", "interpreted_only"}:
            st.success("Adapter invocation completed.")
        else:
            st.error(result.message)

result = st.session_state.get("latest_adapter_invocation_result")
if result is not None:
    st.subheader("Invocation Result")
    st.write(f"Adapter: `{result.adapter_name}`")
    st.write(f"Tool: `{result.tool_name}`")
    st.write(f"Status: `{result.status}`")
    st.write(f"Trace ID: `{result.trace_id or 'N/A'}`")
    st.caption(result.message)
    if result.tool_response is not None:
        st.json(result.tool_response)
