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


def render_home_page() -> None:
    """Render the Chinese launchpad page used by the sidebar navigation."""
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
                    restore_agent_session_to_state(
                        session,
                        source_label=str(latest_snapshot),
                    )
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
        st.page_link(PAGE_BY_KEY["upload"], label="1. 上传文件", icon="📤", use_container_width=True)
        st.page_link(PAGE_BY_KEY["diagnosis"], label="2. 开始诊断", icon="🔎", use_container_width=True)
        st.page_link(PAGE_BY_KEY["review"], label="3. 进入评审", icon="🗂", use_container_width=True)
        st.page_link(PAGE_BY_KEY["reports"], label="4. 导出报告", icon="📦", use_container_width=True)

    st.subheader("维护者入口")
    maintainer_cols = st.columns(4)
    maintainer_links = [
        (PAGE_BY_KEY["intent_runner"], "意图运行器", "🧭"),
        (PAGE_BY_KEY["agent_shell"], "Agent 控制台", "⌨️"),
        (PAGE_BY_KEY["quality_rules"], "质量规则", "✅"),
        (PAGE_BY_KEY["control_plane"], "配置控制面", "⚙️"),
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

    st.caption("左侧功能树已按治理流程分组，适合继续处理、回放或维护。")


PAGE_BY_KEY = {
    "home": st.Page(render_home_page, title="治理启动台", icon="🏠", default=True),
    "upload": st.Page("pages/01_upload.py", title="01 上传元数据", icon="📤"),
    "diagnosis": st.Page("pages/02_diagnosis.py", title="02 诊断工作台", icon="🔎"),
    "review": st.Page("pages/04_review.py", title="03 人工评审", icon="🗂"),
    "reports": st.Page("pages/03_reports.py", title="04 导出报告", icon="📦"),
    "intent_runner": st.Page("pages/05_intent_runner.py", title="意图运行器", icon="🧭"),
    "agent_shell": st.Page("pages/06_agent_shell.py", title="Agent 控制台", icon="⌨️"),
    "tool_console": st.Page("pages/07_tool_console.py", title="工具控制台", icon="🧰"),
    "adapter_console": st.Page("pages/09_adapter_console.py", title="适配器控制台", icon="🔌"),
    "control_plane": st.Page("pages/08_control_plane.py", title="配置控制面", icon="⚙️"),
    "quality_rules": st.Page("pages/10_quality_rules.py", title="质量规则评审", icon="✅"),
    "execution_package": st.Page("pages/11_execution_package.py", title="执行准备包", icon="🧾"),
    "readiness": st.Page("pages/12_governance_readiness.py", title="治理就绪度", icon="📊"),
    "backlog": st.Page("pages/13_governance_backlog.py", title="治理待办", icon="📌"),
    "portfolio": st.Page("pages/14_governance_portfolio.py", title="治理组合视图", icon="📈"),
    "delivery": st.Page("pages/15_governance_delivery.py", title="治理交付包", icon="🚚"),
    "batch": st.Page("pages/16_batch_incremental.py", title="批处理与增量重跑", icon="🔁"),
    "confirmation_import": st.Page("pages/17_confirmation_import.py", title="确认结果导入", icon="📥"),
    "domain_templates": st.Page("pages/18_domain_and_templates.py", title="领域治理包与项目模板", icon="🧩"),
    "metadata_intake": st.Page("pages/19_metadata_intake.py", title="企业元数据接入", icon="🗃"),
}

navigation = st.navigation(
    {
        "开始": [PAGE_BY_KEY["home"]],
        "核心流程": [
            PAGE_BY_KEY["upload"],
            PAGE_BY_KEY["diagnosis"],
            PAGE_BY_KEY["review"],
            PAGE_BY_KEY["reports"],
        ],
        "智能入口": [
            PAGE_BY_KEY["intent_runner"],
            PAGE_BY_KEY["agent_shell"],
            PAGE_BY_KEY["tool_console"],
            PAGE_BY_KEY["adapter_console"],
        ],
        "治理管理": [
            PAGE_BY_KEY["control_plane"],
            PAGE_BY_KEY["quality_rules"],
            PAGE_BY_KEY["execution_package"],
            PAGE_BY_KEY["readiness"],
            PAGE_BY_KEY["backlog"],
            PAGE_BY_KEY["portfolio"],
        ],
        "交付与批处理": [
            PAGE_BY_KEY["delivery"],
            PAGE_BY_KEY["batch"],
            PAGE_BY_KEY["confirmation_import"],
        ],
        "模板与接入": [
            PAGE_BY_KEY["domain_templates"],
            PAGE_BY_KEY["metadata_intake"],
        ],
    },
    expanded=True,
)
navigation.run()
