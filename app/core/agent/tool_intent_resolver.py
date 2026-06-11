"""Resolve selected agent-shell requests into safe local tool calls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.normalize import clean_text


@dataclass(frozen=True)
class AgentToolIntent:
    """Resolved local tool call intent for the agent shell."""

    tool_name: str
    arguments: dict[str, object] = field(default_factory=dict)
    matched_keywords: list[str] = field(default_factory=list)
    summary: str = ""
    requires_confirmation: bool = False


_LEARNING_MEMORY_PREFIX_KEYWORDS = (
    "learning memory",
    "learning-memory",
    "learned memory",
    "review learning",
    "memory learning",
    "学习记忆",
    "学习内存",
    "学习缓存",
    "复核学习",
    "评审学习",
    "算法学习",
)

_TOOL_KEYWORDS: tuple[tuple[str, tuple[str, ...], bool, str], ...] = (
    (
        "rebuild_review_learning",
        (
            "rebuild review learning",
            "rebuild learning",
            "rebuild memory",
            "retrain review learning",
            "重新学习",
            "重建学习",
            "重建复核学习",
            "重建评审学习",
            "重新生成学习",
        ),
        True,
        "Rebuild learning memory from saved human review records.",
    ),
    (
        "backup_then_prune_invalid_learning_memory",
        (
            "backup then prune",
            "safe prune",
            "prune invalid",
            "clean invalid learning",
            "清理无效学习",
            "清理无效记忆",
            "备份后清理",
            "安全清理学习",
            "删除无效学习",
        ),
        True,
        "Create a backup before pruning invalid learning-memory records.",
    ),
    (
        "export_learning_maintenance_report",
        (
            "export learning report",
            "export maintenance report",
            "导出学习报告",
            "导出维护报告",
            "导出学习记忆报告",
        ),
        False,
        "Export a learning-memory maintenance report.",
    ),
    (
        "learning_maintenance_report",
        (
            "maintenance report",
            "learning report",
            "memory report",
            "维护报告",
            "学习报告",
            "学习记忆报告",
        ),
        False,
        "Build a learning-memory maintenance report.",
    ),
    (
        "create_learning_memory_backup",
        (
            "create backup",
            "backup learning",
            "backup memory",
            "备份学习",
            "备份学习记忆",
            "创建学习备份",
        ),
        False,
        "Create a learning-memory backup.",
    ),
    (
        "list_learning_memory_backups",
        (
            "list backup",
            "list backups",
            "show backups",
            "备份列表",
            "查看备份",
            "列出备份",
        ),
        False,
        "List learning-memory backups.",
    ),
    (
        "learning_health_details",
        (
            "health details",
            "memory details",
            "learning details",
            "学习明细",
            "记忆明细",
            "健康明细",
        ),
        False,
        "Load learning-memory health details.",
    ),
    (
        "learning_health",
        (
            "health",
            "check learning",
            "learning health",
            "memory health",
            "检查学习",
            "学习健康",
            "记忆健康",
            "学习记忆健康",
        ),
        False,
        "Build a learning-memory health summary.",
    ),
)

_MEMORY_TYPE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("standard_mapping", ("standard mapping", "mapping", "标准映射", "映射")),
    ("stg_standardization", ("stg", "stg standardization", "stg标准化", "stg结构")),
    ("quality_rules", ("quality rules", "quality", "质量规则", "规则")),
)


def _contains_any(cleaned_text: str, keywords: tuple[str, ...]) -> list[str]:
    matched: list[str] = []
    for keyword in keywords:
        normalized = clean_text(keyword)
        if normalized and normalized in cleaned_text:
            matched.append(keyword)
    return matched


def _extract_positive_int(cleaned_text: str, key: str) -> int | None:
    patterns = (
        rf"{key}\s*[:=]?\s*(\d+)",
        rf"(\d+)\s+{key}",
    )
    for pattern in patterns:
        match = re.search(pattern, cleaned_text)
        if match:
            return max(0, int(match.group(1)))
    return None


def _extract_quoted_value(text: str, key: str) -> str | None:
    patterns = (
        rf"{key}\s*[:=]\s*['\"]([^'\"]+)['\"]",
        rf"{key}\s+['\"]([^'\"]+)['\"]",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _build_learning_arguments(
    tool_name: str,
    text: str,
    cleaned_text: str,
) -> dict[str, object]:
    arguments: dict[str, object] = {}
    backup_limit = _extract_positive_int(cleaned_text, "backup_limit")
    if backup_limit is not None and tool_name in {
        "learning_maintenance_report",
        "export_learning_maintenance_report",
    }:
        arguments["backup_limit"] = backup_limit

    if tool_name == "export_learning_maintenance_report":
        output_dir = _extract_quoted_value(text, "output_dir")
        base_filename = _extract_quoted_value(text, "base_filename")
        if output_dir:
            arguments["output_dir"] = output_dir
        if base_filename:
            arguments["base_filename"] = base_filename

    if tool_name == "rebuild_review_learning":
        memory_types = [
            memory_type
            for memory_type, keywords in _MEMORY_TYPE_KEYWORDS
            if _contains_any(cleaned_text, keywords)
        ]
        if memory_types:
            arguments["memory_types"] = memory_types
        if any(
            phrase in cleaned_text
            for phrase in ("no backup", "without backup", "不备份", "无需备份")
        ):
            arguments["create_backup"] = False

    return arguments


def resolve_agent_tool_intent(text: str) -> AgentToolIntent | None:
    """Resolve a narrow set of agent-shell maintenance requests to local tools."""
    cleaned_text = clean_text(text or "")
    if not cleaned_text:
        return None

    prefix_matches = _contains_any(cleaned_text, _LEARNING_MEMORY_PREFIX_KEYWORDS)
    for tool_name, keywords, requires_confirmation, summary in _TOOL_KEYWORDS:
        action_matches = _contains_any(cleaned_text, keywords)
        if not action_matches:
            continue
        if tool_name in {"learning_health", "learning_health_details"}:
            if not prefix_matches and not any(
                marker in cleaned_text
                for marker in ("learning", "memory", "学习", "记忆")
            ):
                continue
        elif not prefix_matches:
            continue
        arguments = _build_learning_arguments(tool_name, text, cleaned_text)
        return AgentToolIntent(
            tool_name=tool_name,
            arguments=arguments,
            matched_keywords=[*prefix_matches, *action_matches],
            summary=summary,
            requires_confirmation=requires_confirmation,
        )
    return None
