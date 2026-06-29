"""Governance delivery package page."""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_workflow_result,
    initialize_session_state,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.delivery.delivery_service import DeliveryService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_delivery_package_with_review_from_file,
)
from app.ui.page_overview import build_workflow_overview
from app.ui.performance_helpers import (
    render_json_section,
    render_records_dataframe_section,
)
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import render_key_value_block, render_page_header

initialize_session_state()

render_page_header(
    "治理交付包",
    "构建确认工作簿和本地治理交付包。",
)

uploaded_file_path = get_current_input_file_path()
current_result: WorkflowResult | None = get_workflow_result()
output_dir = st.text_input(
    "输出目录",
    value=str(PROJECT_ROOT / "outputs" / "delivery_packages"),
)
base_name = st.text_input("交付包或工作簿基础名称", value="governance_delivery_package")

service = DeliveryService()
col_workbooks, col_package = st.columns(2)

with col_workbooks:
    if st.button("构建确认工作簿"):
        if current_result is None and not uploaded_file_path:
            st.warning("请先运行工作流或上传元数据文件。")
        else:
            try:
                with st.spinner("正在构建确认工作簿..."):
                    if current_result is None:
                        current_result = run_full_governance_delivery_package_with_review_from_file(
                            uploaded_file_path
                        )
                    workbook_results = service.build_confirmation_workbooks(
                        current_result,
                        output_dir=output_dir,
                        base_name=base_name,
                    )
                    current_result.confirmation_workbook_results = workbook_results
                    set_workflow_result_state(current_result)
            except Exception as exc:
                st.error(f"构建确认工作簿失败: {exc}")
            else:
                st.success("确认工作簿已生成。")

with col_package:
    if st.button("构建治理交付包", type="primary"):
        if current_result is None and not uploaded_file_path:
            st.warning("请先运行工作流或上传元数据文件。")
        else:
            try:
                with st.spinner("正在构建治理交付包..."):
                    if uploaded_file_path:
                        current_result = run_full_governance_delivery_package_with_review_from_file(
                            uploaded_file_path
                        )
                    else:
                        current_result = service.build_governance_delivery_package(
                            current_result,
                            output_dir=output_dir,
                            base_name=base_name,
                        )
                    set_workflow_result_state(current_result)
            except Exception as exc:
                st.error(f"构建交付包失败: {exc}")
            else:
                st.success("治理交付包已生成。")

result: WorkflowResult | None = get_workflow_result()
if result is None:
    st.info("构建交付包后可查看生成的交付物路径。")
    st.stop()

render_result_overview(
    build_workflow_overview(
        result,
        title="交付总览",
        next_step="先看交付物，再下载工作簿或交付清单。",
    )
)

st.subheader("已生成工作簿")
if result.confirmation_workbook_results:
    render_records_dataframe_section(
        "已生成工作簿",
        result.confirmation_workbook_results,
        key_prefix="delivery_workbooks",
    )
else:
    st.info("暂无已生成确认工作簿。")

st.subheader("交付包")
if result.governance_delivery_package_result is not None:
    package_result = result.governance_delivery_package_result
    render_key_value_block(
        None,
        rows=[("输出目录", package_result.output_dir)],
    )
    render_json_section("已生成文件", package_result.generated_files, compact=True)
else:
    st.info("暂无已生成交付包。")

st.subheader("交付清单预览")
if result.governance_delivery_manifest is not None:
    render_json_section("交付清单预览", result.governance_delivery_manifest, compact=True)
else:
    st.info("构建交付包后会显示交付清单。")

