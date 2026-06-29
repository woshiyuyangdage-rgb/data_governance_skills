"""Batch processing and incremental rerun page."""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_batch_file_paths,
    get_workflow_result,
    initialize_session_state,
    set_batch_file_paths,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.reports.report_service import export_all_reports
from app.core.utils.file_utils import save_uploaded_file
from app.ui.performance_helpers import (
    render_json_section,
    render_records_dataframe_section,
)
from app.ui.status_blocks import render_key_value_block, render_page_header

initialize_session_state()

render_page_header(
    "批处理与增量重跑",
    "基于本地快照运行多文件批处理和仅变更对象重跑。",
)

uploaded_files = st.file_uploader(
    "选择元数据文件",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
)
group_by = st.selectbox(
    "分组字段",
    options=["system_name", "schema_name", "domain_hint"],
)
batch_name = st.text_input("批次名称", value="default_batch_governance")
upload_dir = PROJECT_ROOT / "outputs" / "batch_uploads"

if uploaded_files:
    saved_paths = [
        save_uploaded_file(uploaded_file, upload_dir)
        for uploaded_file in uploaded_files
    ]
    set_batch_file_paths(saved_paths)
    st.success(f"已保存 {len(saved_paths)} 个文件用于批处理。")

file_paths = get_batch_file_paths()
render_key_value_block(
    None,
    rows=[("已选文件数", len(file_paths))],
)

engine = WorkflowEngine()
col_full, col_incremental, col_export = st.columns(3)

with col_full:
    if st.button("完整批处理运行", type="primary"):
        if not file_paths:
            st.warning("请先上传一个或多个元数据文件。")
        else:
            with st.spinner("正在运行完整批处理治理..."):
                result = engine.run_batch_governance_workflow(
                    file_paths=file_paths,
                    group_by=group_by,
                    changed_only=False,
                    batch_name=batch_name,
                )
            set_workflow_result_state(result)
            st.success("批处理治理运行完成。")

with col_incremental:
    if st.button("仅变更对象重跑"):
        if not file_paths:
            st.warning("请先上传一个或多个元数据文件。")
        else:
            with st.spinner("正在运行仅变更对象重跑..."):
                result = engine.run_batch_governance_workflow(
                    file_paths=file_paths,
                    group_by=group_by,
                    changed_only=True,
                    batch_name=batch_name,
                )
            set_workflow_result_state(result)
            st.success("仅变更对象重跑完成。")

with col_export:
    if st.button("导出批处理报告"):
        result = get_workflow_result()
        if result is None:
            st.warning("请先运行批处理。")
        else:
            paths = export_all_reports(
                result,
                str(PROJECT_ROOT / "outputs" / "reports"),
                f"{batch_name}_batch_report",
            )
            st.success(f"批处理报告已导出: {paths['json']}")

result = get_workflow_result()
if result is None:
    st.info("运行批处理后可查看汇总。")
    st.stop()

st.subheader("批处理分组汇总")
if result.batch_group_results:
    render_records_dataframe_section(
        "批处理分组汇总",
        result.batch_group_results,
        key_prefix="batch_group_summary",
    )
else:
    st.info("暂无已处理批次分组。")

st.subheader("增量差异汇总")
if result.incremental_diff_summary is not None:
    render_json_section("增量差异汇总", result.incremental_diff_summary)
else:
    st.info("暂无差异汇总。")

st.subheader("差异明细")
if result.incremental_diff_items:
    render_records_dataframe_section(
        "差异明细",
        result.incremental_diff_items,
        key_prefix="batch_diff_items",
    )
else:
    st.info("暂无差异明细。")

st.subheader("重跑范围汇总")
render_json_section("重跑范围汇总", result.rerun_scope_summary)

