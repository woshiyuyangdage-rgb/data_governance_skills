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
ADAPTER_MODE_LABELS = {
    "native": "本地格式",
    "openai_style": "OpenAI 风格",
    "manifest": "能力清单格式",
}

default_arguments = build_adapter_console_default_arguments(
    get_uploaded_file_path(),
    get_workflow_result(),
)

render_page_header(
    "适配器控制台",
    (
        "查看适配器可消费的能力清单和结构定义，并通过本地或 OpenAI 风格格式调用本地工具平台。"
    ),
)

st.subheader("能力清单")
render_metric_row(
    [
        ("服务", manifest.service_name),
        ("版本", manifest.version),
        ("工具数", len(manifest.tools)),
    ],
)
st.caption(manifest.description)

with st.expander("能力清单 JSON", expanded=False):
    render_json_section("能力清单 JSON", manifest, compact=True)

tab_native, tab_openai, tab_mcp = st.tabs(
    ["本地结构定义", "OpenAI 风格结构定义", "MCP 风格清单"]
)

with tab_native:
    render_json_section(
        "本地结构定义",
        records_to_dataframe(native_schemas).to_dict("records"),
        compact=True,
    )

with tab_openai:
    render_json_section("OpenAI 风格结构定义", openai_schemas, compact=True)

with tab_mcp:
    render_json_section("MCP 风格清单", mcp_manifest, compact=True)

st.subheader("本地适配器调用")
adapter_mode = st.selectbox(
    "适配器模式",
    options=["native", "openai_style", "manifest"],
    format_func=lambda value: ADAPTER_MODE_LABELS.get(value, value),
)
selected_tool_name = st.selectbox("工具", options=tool_names)
selected_schema = native_schema_lookup[selected_tool_name]
st.caption(
    f"分类: {selected_schema.category or '未知'} | "
    f"说明: {selected_schema.description}"
)

default_arguments_json = json.dumps(
    default_arguments.get(selected_tool_name, {}),
    ensure_ascii=False,
    indent=2,
)
arguments_text = st.text_area(
    "参数",
    value=default_arguments_json,
    height=220,
    key=f"adapter_console_arguments_{adapter_mode}_{selected_tool_name}",
)

if st.button("通过适配器调用", type="primary"):
    try:
        parsed_arguments = json.loads(arguments_text or "{}")
        if not isinstance(parsed_arguments, dict):
            raise ValueError("参数必须是 JSON 对象。")
        if adapter_mode == "native":
            result = adapter.invoke_native_tool(selected_tool_name, parsed_arguments)
        elif adapter_mode == "openai_style":
            result = adapter.invoke_openai_style(selected_tool_name, arguments_text)
        else:
            result = adapter.invoke_manifest_tool(selected_tool_name, parsed_arguments)
    except Exception as exc:
        st.error(f"适配器调用失败: {exc}")
    else:
        set_latest_adapter_invocation_result(result)
        if result.status in {"success", "executed_successfully", "interpreted_only"}:
            st.success("适配器调用完成。")
        else:
            st.error(result.message)

result = get_latest_adapter_invocation_result()
if result is not None:
    render_key_value_block(
        "调用结果",
        summary=result.message,
        rows=[
            ("适配器", result.adapter_name),
            ("工具", result.tool_name),
            ("状态", result.status),
            ("执行跟踪 ID", result.trace_id or "N/A"),
        ],
    )
    if result.tool_response is not None:
        render_json_section("工具响应", result.tool_response, compact=True)
