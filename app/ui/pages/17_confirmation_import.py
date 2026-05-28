"""Confirmation workbook import page."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    get_confirmation_import_file_path,
    get_confirmation_template_diagnosis,
    get_confirmation_validation_result,
    ensure_project_root_on_path,
    get_workflow_result,
    initialize_session_state,
    set_confirmation_import_file_path,
    set_confirmation_template_diagnosis,
    set_confirmation_validation_result,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.delivery.confirmation_template_loader import (
    list_enabled_confirmation_template_profiles,
)
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.utils.file_utils import save_uploaded_file
from app.ui.performance_helpers import render_json_section, render_records_dataframe_section
from app.ui.status_blocks import render_page_header
from app.ui.workbench_cache import (
    diagnose_confirmation_template_cached,
    file_cache_key,
    validate_confirmation_workbook_cached,
)

initialize_session_state()

render_page_header(
    "确认结果导入",
    (
        "校验确认工作簿、诊断模板、导入合并，并准备变更对象重跑范围。"
    ),
)

WORKBOOK_TYPE_LABELS = {
    "mapping_confirmation": "标准映射确认",
    "stg_confirmation": "STG 设计确认",
    "quality_rule_confirmation": "质量规则确认",
    "backlog_confirmation": "治理待办确认",
}
TEMPLATE_LABELS = {
    "auto_match": "自动匹配",
}

uploaded_file = st.file_uploader("上传确认工作簿", type=["xlsx", "csv"])
workbook_type = st.selectbox(
    "工作簿类型",
    options=[
        "mapping_confirmation",
        "stg_confirmation",
        "quality_rule_confirmation",
        "backlog_confirmation",
    ],
    format_func=lambda value: WORKBOOK_TYPE_LABELS.get(value, value),
)
template_options = ["auto_match"] + [
    profile.template_name for profile in list_enabled_confirmation_template_profiles()
]
selected_template = st.selectbox(
    "确认模板",
    template_options,
    format_func=lambda value: TEMPLATE_LABELS.get(value, value),
)

if uploaded_file is not None:
    saved_path = save_uploaded_file(uploaded_file, PROJECT_ROOT / "outputs" / "confirmation_imports")
    set_confirmation_import_file_path(saved_path)
    st.success(f"工作簿已保存: {saved_path}")

file_path = get_confirmation_import_file_path()
importer = ConfirmationWorkbookImporter()
engine = WorkflowEngine()

col_validate, col_diagnose, col_import, col_rerun = st.columns(4)
with col_validate:
    if st.button("校验工作簿"):
        if not file_path:
            st.warning("请先上传确认工作簿。")
        else:
            validation = validate_confirmation_workbook_cached(
                file_path,
                workbook_type,
                file_cache_key(file_path),
            )
            set_confirmation_validation_result(validation.model_dump())

with col_diagnose:
    if st.button("诊断确认模板"):
        if not file_path:
            st.warning("请先上传确认工作簿。")
        else:
            diagnosis = diagnose_confirmation_template_cached(
                file_path,
                workbook_type,
                file_cache_key(file_path),
            )
            set_confirmation_template_diagnosis(diagnosis.model_dump())

with col_import:
    if st.button("导入并合并", type="primary"):
        if not file_path:
            st.warning("请先上传确认工作簿。")
        else:
            template_name = None if selected_template == "auto_match" else selected_template
            result = engine.import_confirmation_with_template(
                file_path,
                template_name=template_name,
                workbook_type=workbook_type,
            )
            set_workflow_result_state(result)
            st.success("工作簿已导入并合并。")

with col_rerun:
    if st.button("导入并重跑变更对象"):
        if not file_path:
            st.warning("请先上传确认工作簿。")
        else:
            template_name = None if selected_template == "auto_match" else selected_template
            result = engine.import_confirmation_with_template_and_rerun(
                file_path,
                template_name=template_name,
                workbook_type=workbook_type,
                rerun_changed_only=True,
            )
            set_workflow_result_state(result)
            st.success("工作簿已导入，重跑范围已准备。")

st.subheader("校验结果")
confirmation_validation_result = get_confirmation_validation_result()
if confirmation_validation_result:
    render_json_section("校验结果", confirmation_validation_result)
else:
    st.info("校验工作簿后可查看结果。")

st.subheader("模板诊断")
confirmation_template_diagnosis = get_confirmation_template_diagnosis()
if confirmation_template_diagnosis:
    render_json_section("模板诊断", confirmation_template_diagnosis)
else:
    st.info("诊断工作簿模板后可查看匹配模板和映射证据。")

result = get_workflow_result()
if result is not None and result.workbook_import_summaries:
    st.subheader("导入汇总")
    render_records_dataframe_section(
        "导入汇总",
        result.workbook_import_summaries,
        key_prefix="confirmation_import_summary",
    )
    st.subheader("回写结果")
    render_records_dataframe_section(
        "回写结果",
        result.roundtrip_results,
        key_prefix="confirmation_roundtrip_results",
    )
    st.subheader("变更对象汇总")
    render_json_section("变更对象汇总", result.roundtrip_changed_objects_summary)
    if result.confirmation_template_match_result:
        st.subheader("确认模板匹配")
        render_json_section("确认模板匹配", result.confirmation_template_match_result)
    if result.confirmation_template_mapping_result:
        st.subheader("确认模板映射")
        render_json_section("确认模板映射", result.confirmation_template_mapping_result)
    st.subheader("重跑范围")
    render_json_section("重跑范围", result.rerun_scope_summary)

