"""Streamlit workbench homepage."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    INPUT_TEMPLATE_DOC_PATH,
    SAMPLE_METADATA_PATH,
    get_agent_shell_session_id,
    get_restored_session_id,
    get_restored_session_source,
    ensure_project_root_on_path,
    initialize_session_state,
    restore_agent_session_to_state,
    set_uploaded_file_state,
)
from app.ui.workbench_cache import (
    content_signature,
    file_cache_key,
    read_csv_dataframe_cached,
    read_file_bytes_cached,
)
from app.ui.status_blocks import render_key_value_block, render_page_header

ensure_project_root_on_path()
st.set_page_config(page_title="数据治理技能工作台", layout="wide")
initialize_session_state()

from app.core.agent.session_store import load_latest_session_snapshot, list_session_snapshots

render_page_header(
    "治理启动台",
    "先上传，再诊断，再评审，最后导出。治理能力也可以进入意图、Agent 和控制面。",
    caption=f"输入模板: `{INPUT_TEMPLATE_DOC_PATH}` | 示例元数据: `{SAMPLE_METADATA_PATH}`",
)

top_left, top_right = st.columns([2, 1])

with top_left:
    st.subheader("恢复上次会话")
    snapshots = list_session_snapshots()
    if snapshots:
        latest_snapshot = snapshots[0]
        st.caption(f"最近会话快照: {latest_snapshot.name}")
        if st.button("恢复最近会话", use_container_width=True):
            session = load_latest_session_snapshot()
            if session is None:
                st.warning("没有可恢复的会话快照。")
            else:
                restore_agent_session_to_state(session, source_label=str(latest_snapshot))
                st.success(f"已恢复会话 {session.session_id}")
    else:
        st.info("还没有可恢复的会话快照。")

with top_right:
    render_key_value_block(
        "当前状态",
        rows=[
            ("读取模板", INPUT_TEMPLATE_DOC_PATH.name),
            ("示例数据", SAMPLE_METADATA_PATH.name),
            ("当前会话", get_agent_shell_session_id() or "N/A"),
        ],
    )

demo_left, demo_right = st.columns(2)

with demo_left:
    st.subheader("示例数据")
    sample_cache_token = file_cache_key(str(SAMPLE_METADATA_PATH))
    sample_bytes = read_file_bytes_cached(str(SAMPLE_METADATA_PATH), sample_cache_token)
    sample_df = read_csv_dataframe_cached(str(SAMPLE_METADATA_PATH), sample_cache_token)
    st.dataframe(sample_df.head(8), use_container_width=True)
    if st.button("载入示例数据", use_container_width=True):
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

with demo_right:
    st.subheader("一键入口")
    st.page_link("pages/01_upload.py", label="1. 上传文件", icon="📤", use_container_width=True)
    st.page_link("pages/02_diagnosis.py", label="2. 开始诊断", icon="🔎", use_container_width=True)
    st.page_link("pages/04_review.py", label="3. 进入评审", icon="🗂", use_container_width=True)
    st.page_link("pages/03_reports.py", label="4. 导出报告", icon="📦", use_container_width=True)

st.subheader("维护者入口")
maintainer_cols = st.columns(4)
maintainer_links = [
    ("pages/05_intent_runner.py", "意图运行器", "🧭"),
    ("pages/06_agent_shell.py", "Agent 控制台", "⌨️"),
    ("pages/10_quality_rules.py", "质量规则", "✅"),
    ("pages/08_control_plane.py", "配置控制面", "⚙️"),
]
for column, (page, label, icon) in zip(maintainer_cols, maintainer_links, strict=True):
    with column:
        st.page_link(page, label=label, icon=icon, use_container_width=True)

restored_session_id = get_restored_session_id()
if restored_session_id:
    st.info(
        f"已恢复会话 `{restored_session_id}` "
        f"来自 `{get_restored_session_source() or 'N/A'}`"
    )

st.caption("侧边栏保留更多页面，适合继续处理、回放或维护。")
