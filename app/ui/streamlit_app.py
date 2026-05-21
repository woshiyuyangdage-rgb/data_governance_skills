"""Streamlit workbench homepage."""

import hashlib
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    INPUT_TEMPLATE_DOC_PATH,
    SAMPLE_METADATA_PATH,
    ensure_project_root_on_path,
    initialize_session_state,
    restore_agent_session_to_state,
)

ensure_project_root_on_path()
st.set_page_config(page_title="Data Governance Skills Workbench", layout="wide")
initialize_session_state()

from app.core.agent.session_store import load_latest_session_snapshot, list_session_snapshots

st.title("治理启动台")
st.write("先上传，再诊断，再评审，最后导出。治理能力也可以进入意图、Agent 和控制面。")
st.caption(f"输入模板: `{INPUT_TEMPLATE_DOC_PATH}` | 示例元数据: `{SAMPLE_METADATA_PATH}`")

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
    st.subheader("当前状态")
    st.write(f"- 读取模板: `{INPUT_TEMPLATE_DOC_PATH.name}`")
    st.write(f"- 示例数据: `{SAMPLE_METADATA_PATH.name}`")
    st.write(
        f"- 当前会话: `{st.session_state.get('agent_shell_session_id') or 'N/A'}`"
    )

demo_left, demo_right = st.columns(2)

with demo_left:
    st.subheader("示例数据")
    sample_df = pd.read_csv(SAMPLE_METADATA_PATH)
    st.dataframe(sample_df.head(8), use_container_width=True)
    if st.button("载入示例数据", use_container_width=True):
        sample_bytes = SAMPLE_METADATA_PATH.read_bytes()
        st.session_state["uploaded_file_path"] = str(SAMPLE_METADATA_PATH)
        st.session_state["uploaded_file_name"] = SAMPLE_METADATA_PATH.name
        st.session_state["uploaded_file_size"] = SAMPLE_METADATA_PATH.stat().st_size
        st.session_state["uploaded_file_extension"] = SAMPLE_METADATA_PATH.suffix.lstrip(".")
        st.session_state["uploaded_file_signature"] = hashlib.md5(sample_bytes).hexdigest()
        st.session_state["workflow_result"] = None
        st.session_state["workflow_result_file_path"] = None
        st.session_state["latest_report_paths"] = {}
        st.session_state["restored_session_source"] = "sample_metadata"
        st.success("示例数据已载入，可以直接进入上传或诊断页面。")
    st.download_button(
        label="下载示例 CSV",
        data=SAMPLE_METADATA_PATH.read_bytes(),
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
    ("pages/05_intent_runner.py", "Intent Runner", "🧭"),
    ("pages/06_agent_shell.py", "Agent Shell", "⌨️"),
    ("pages/10_quality_rules.py", "Quality Rules", "✅"),
    ("pages/08_control_plane.py", "Control Plane", "⚙️"),
]
for column, (page, label, icon) in zip(maintainer_cols, maintainer_links, strict=True):
    with column:
        st.page_link(page, label=label, icon=icon, use_container_width=True)

if st.session_state.get("restored_session_id"):
    st.info(
        f"已恢复会话 `{st.session_state['restored_session_id']}` "
        f"来自 `{st.session_state.get('restored_session_source') or 'N/A'}`"
    )

st.caption("侧边栏保留更多页面，适合继续处理、回放或维护。")
