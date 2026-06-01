"""Chinese Streamlit navigation registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class PageDefinition:
    """Static page metadata shared by the sidebar and homepage links."""

    key: str
    target: str | Callable[[], None]
    title: str
    icon: str
    default: bool = False
    quick_start_label: str | None = None
    maintainer_label: str | None = None


PAGE_DEFINITIONS: tuple[PageDefinition, ...] = (
    PageDefinition("home", "home", "治理启动台", "🏠", default=True),
    PageDefinition("upload", "pages/01_upload.py", "01 上传元数据", "📤", quick_start_label="1. 上传文件"),
    PageDefinition("diagnosis", "pages/02_diagnosis.py", "02 诊断工作台", "🔎", quick_start_label="2. 开始诊断"),
    PageDefinition("review", "pages/04_review.py", "03 人工评审", "🗂", quick_start_label="3. 进入评审"),
    PageDefinition("reports", "pages/03_reports.py", "04 导出报告", "📦", quick_start_label="4. 导出报告"),
    PageDefinition("intent_runner", "pages/05_intent_runner.py", "意图运行器", "🧭", maintainer_label="意图运行器"),
    PageDefinition("agent_shell", "pages/06_agent_shell.py", "Agent 控制台", "⌨️", maintainer_label="Agent 控制台"),
    PageDefinition("tool_console", "pages/07_tool_console.py", "工具控制台", "🧰"),
    PageDefinition("adapter_console", "pages/09_adapter_console.py", "适配器控制台", "🔌"),
    PageDefinition("control_plane", "pages/08_control_plane.py", "配置控制面", "⚙️", maintainer_label="配置控制面"),
    PageDefinition("quality_rules", "pages/10_quality_rules.py", "质量规则评审", "✅", maintainer_label="质量规则"),
    PageDefinition("execution_package", "pages/11_execution_package.py", "执行准备包", "🧾"),
    PageDefinition("readiness", "pages/12_governance_readiness.py", "治理就绪度", "📊"),
    PageDefinition("backlog", "pages/13_governance_backlog.py", "治理待办", "📌"),
    PageDefinition("portfolio", "pages/14_governance_portfolio.py", "治理组合视图", "📈"),
    PageDefinition("delivery", "pages/15_governance_delivery.py", "治理交付包", "🚚"),
    PageDefinition("batch", "pages/16_batch_incremental.py", "批处理与增量重跑", "🔁"),
    PageDefinition("confirmation_import", "pages/17_confirmation_import.py", "确认结果导入", "📥"),
    PageDefinition("domain_templates", "pages/18_domain_and_templates.py", "领域治理包与项目模板", "🧩"),
    PageDefinition("metadata_intake", "pages/19_metadata_intake.py", "企业元数据接入", "🗃"),
)


NAVIGATION_SECTION_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("开始", ("home",)),
    ("核心流程", ("upload", "diagnosis", "review", "reports")),
    ("智能入口", ("intent_runner", "agent_shell", "tool_console", "adapter_console")),
    (
        "治理管理",
        (
            "control_plane",
            "quality_rules",
            "execution_package",
            "readiness",
            "backlog",
            "portfolio",
        ),
    ),
    ("交付与批处理", ("delivery", "batch", "confirmation_import")),
    ("模板与接入", ("domain_templates", "metadata_intake")),
)


def build_page_registry(home_page: Callable[[], None]) -> dict[str, Any]:
    """Build the Streamlit page registry used by the Chinese sidebar tree."""
    page_by_key: dict[str, Any] = {}
    for definition in PAGE_DEFINITIONS:
        target = home_page if definition.key == "home" else definition.target
        page_by_key[definition.key] = st.Page(
            target,
            title=definition.title,
            icon=definition.icon,
            default=definition.default,
        )
    return page_by_key


def build_navigation_sections(
    page_by_key: dict[str, Any],
) -> dict[str, list[Any]]:
    """Build grouped Chinese sidebar sections."""
    return {
        section_label: [page_by_key[key] for key in page_keys]
        for section_label, page_keys in NAVIGATION_SECTION_KEYS
    }


def build_quick_start_links(page_by_key: dict[str, Any]) -> list[tuple[Any, str, str]]:
    """Build homepage quick-start links from the shared page metadata."""
    links: list[tuple[Any, str, str]] = []
    for definition in PAGE_DEFINITIONS:
        if definition.quick_start_label:
            links.append(
                (
                    page_by_key[definition.key],
                    definition.quick_start_label,
                    definition.icon,
                )
            )
    return links


def build_maintainer_links(page_by_key: dict[str, Any]) -> list[tuple[Any, str, str]]:
    """Build homepage maintainer links from the shared page metadata."""
    links: list[tuple[Any, str, str]] = []
    for definition in PAGE_DEFINITIONS:
        if definition.maintainer_label:
            links.append(
                (
                    page_by_key[definition.key],
                    definition.maintainer_label,
                    definition.icon,
                )
            )
    return links
