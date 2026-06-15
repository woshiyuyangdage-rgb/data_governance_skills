"""Streamlit workbench homepage."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    SAMPLE_METADATA_PATH,
    ensure_project_root_on_path,
    get_uploaded_file_path,
    get_uploaded_file_signature,
    initialize_session_state,
    set_uploaded_file_state,
)
from app.ui.workbench_cache import (
    content_signature,
    file_cache_key,
    read_csv_dataframe_cached,
    read_file_bytes_cached,
)
from app.ui.column_labels import localize_dataframe_columns
from app.ui.navigation import (
    build_maintainer_links,
    build_navigation_sections,
    build_page_registry,
    build_quick_start_links,
)
from app.ui.status_blocks import render_page_header

ensure_project_root_on_path()
st.set_page_config(page_title="数据治理技能工作台", layout="wide")
initialize_session_state()

METADATA_TEMPLATE_COLUMNS = [
    "table_name",
    "table_name_cn",
    "table_description",
    "schema_name",
    "system_name",
    "field_name",
    "field_name_cn",
    "field_description",
    "data_type",
    "nullable",
]


def _metadata_template_csv_bytes() -> bytes:
    """Return an empty metadata CSV template with standard headers."""
    return (",".join(METADATA_TEMPLATE_COLUMNS) + "\n").encode("utf-8")


def _ensure_sample_metadata_as_default(sample_bytes: bytes) -> bool:
    """Register the built-in sample as the active input without clearing results."""
    uploaded_file_path = get_uploaded_file_path()
    sample_signature = content_signature(sample_bytes)
    if (
        uploaded_file_path == str(SAMPLE_METADATA_PATH)
        and get_uploaded_file_signature() == sample_signature
    ):
        return True
    if uploaded_file_path:
        return True

    try:
        set_uploaded_file_state(
            file_path=SAMPLE_METADATA_PATH,
            file_signature=sample_signature,
            source_label="sample_metadata",
            reset_workflow=False,
        )
    except Exception:
        return False
    return True


def render_home_page() -> None:
    """Render the Chinese launchpad page used by the sidebar navigation."""
    render_page_header(
        "治理启动台",
        "先上传，再诊断，再评审，最后导出。治理能力也可以进入意图、Agent 和控制面。",
        caption="内置输入模板和示例元数据已准备好，可直接载入测试。",
    )

    sample_cache_token = file_cache_key(str(SAMPLE_METADATA_PATH))
    sample_bytes = read_file_bytes_cached(
        str(SAMPLE_METADATA_PATH),
        f"bytes::{sample_cache_token}",
    )
    sample_df = read_csv_dataframe_cached(
        str(SAMPLE_METADATA_PATH),
        f"dataframe::{sample_cache_token}",
    )
    sample_is_ready = _ensure_sample_metadata_as_default(sample_bytes)

    sample_title_col, template_download_col = st.columns([3, 1])
    with sample_title_col:
        st.subheader("示例数据")
    with template_download_col:
        st.download_button(
            label="下载元数据模板",
            data=_metadata_template_csv_bytes(),
            file_name="metadata_input_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.caption("以下为内置示例元数据前 10 条，可直接用于页面功能测试。")
    st.table(localize_dataframe_columns(sample_df.head(10)))
    if sample_is_ready:
        st.caption("没有当前输入时，示例数据会自动作为默认输入；已有上传文件时不会被覆盖。")
    else:
        st.warning("示例数据已展示，但未能自动设为默认输入。")
        if st.button("手动载入示例数据", use_container_width=True):
            set_uploaded_file_state(
                file_path=SAMPLE_METADATA_PATH,
                file_signature=content_signature(sample_bytes),
                source_label="sample_metadata",
            )
            st.success("示例数据已载入，可以直接进入上传或诊断页面。")
        st.download_button(
            label="下载示例 CSV",
            data=sample_bytes,
            file_name=SAMPLE_METADATA_PATH.name,
            mime="text/csv",
            use_container_width=True,
        )

    st.subheader("一键入口")
    quick_start_links = build_quick_start_links(PAGE_BY_KEY)
    quick_start_cols = st.columns(len(quick_start_links))
    for column, (page, label, icon) in zip(
        quick_start_cols,
        quick_start_links,
        strict=True,
    ):
        with column:
            st.page_link(page, label=label, icon=icon, use_container_width=True)

    st.subheader("维护者入口")
    maintainer_links = build_maintainer_links(PAGE_BY_KEY)
    maintainer_cols = st.columns(len(maintainer_links))
    for column, (page, label, icon) in zip(maintainer_cols, maintainer_links, strict=True):
        with column:
            st.page_link(page, label=label, icon=icon, use_container_width=True)

    st.caption("左侧功能树已按治理流程分组，适合继续处理、回放或维护。")


PAGE_BY_KEY = build_page_registry(render_home_page)

navigation = st.navigation(
    build_navigation_sections(PAGE_BY_KEY),
    expanded=True,
)
navigation.run()
