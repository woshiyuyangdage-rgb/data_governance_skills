"""Chinese Streamlit navigation registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


def build_page_registry(home_page: Callable[[], None]) -> dict[str, Any]:
    """Build the Streamlit page registry used by the Chinese sidebar tree."""
    return {
        "home": st.Page(home_page, title="治理启动台", icon="🏠", default=True),
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


def build_navigation_sections(
    page_by_key: dict[str, Any],
) -> dict[str, list[Any]]:
    """Build grouped Chinese sidebar sections."""
    return {
        "开始": [page_by_key["home"]],
        "核心流程": [
            page_by_key["upload"],
            page_by_key["diagnosis"],
            page_by_key["review"],
            page_by_key["reports"],
        ],
        "智能入口": [
            page_by_key["intent_runner"],
            page_by_key["agent_shell"],
            page_by_key["tool_console"],
            page_by_key["adapter_console"],
        ],
        "治理管理": [
            page_by_key["control_plane"],
            page_by_key["quality_rules"],
            page_by_key["execution_package"],
            page_by_key["readiness"],
            page_by_key["backlog"],
            page_by_key["portfolio"],
        ],
        "交付与批处理": [
            page_by_key["delivery"],
            page_by_key["batch"],
            page_by_key["confirmation_import"],
        ],
        "模板与接入": [
            page_by_key["domain_templates"],
            page_by_key["metadata_intake"],
        ],
    }
