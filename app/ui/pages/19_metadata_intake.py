"""Streamlit page for enterprise metadata intake adapters."""

import streamlit as st

from app.core.intake.intake_profile_loader import list_enabled_intake_template_profiles
from app.ui.performance_helpers import render_json_section, render_records_dataframe_section
from app.ui.status_blocks import render_page_header
from app.ui.workbench_cache import (
    file_cache_key,
    diagnose_intake_template_cached,
    normalize_metadata_input_cached,
)


render_page_header(
    "企业元数据接入",
    caption="诊断结构化元数据模板，并规范化为标准输入。",
)

profiles = list_enabled_intake_template_profiles()
profile_options = ["auto_match"] + [profile.profile_name for profile in profiles]
PROFILE_OPTION_LABELS = {
    "auto_match": "自动匹配",
}

st.subheader("可用接入配置")
render_records_dataframe_section(
    "可用接入配置",
    profiles,
    key_prefix="intake_profiles",
)

st.subheader("诊断与规范化")
file_path = st.text_input("元数据文件路径")
sheet_name = st.text_input("Sheet 名称（可选）")
selected_profile = st.selectbox(
    "接入配置",
    profile_options,
    format_func=lambda value: PROFILE_OPTION_LABELS.get(value, value),
)

if st.button("诊断模板"):
    if not file_path:
        st.warning("请先提供元数据文件路径。")
    else:
        result = diagnose_intake_template_cached(
            file_path,
            sheet_name=sheet_name or None,
            file_signature=file_cache_key(file_path),
        )
        render_json_section("模板诊断结果", result)

if st.button("规范化输入"):
    if not file_path:
        st.warning("请先提供元数据文件路径。")
    else:
        profile_name = None if selected_profile == "auto_match" else selected_profile
        result = normalize_metadata_input_cached(
            file_path,
            profile_name=profile_name,
            sheet_name=sheet_name or None,
            file_signature=file_cache_key(file_path),
        )
        render_json_section("输入规范化结果", result)
        if result.status == "success":
            st.success(
                f"已规范化 {result.row_count} 行，覆盖 {result.table_count} 张表。"
            )

