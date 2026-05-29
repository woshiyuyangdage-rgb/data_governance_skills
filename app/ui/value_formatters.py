"""Shared value formatting helpers for Streamlit UI blocks."""

from __future__ import annotations

from numbers import Real

DISPLAY_VALUE_LABELS = {
    "unknown": "未知",
    "fallback": "回退解析",
    "keyword": "关键词",
    "local_nlp": "本地 NLP",
    "keyword+local_nlp": "关键词 + 本地 NLP",
    "preview": "预览",
    "preview_requires_confirmation": "预览待确认",
    "interpreted_only": "仅解析",
    "executed_successfully": "执行成功",
    "validation_failed": "校验失败",
    "success": "成功",
    "failed": "失败",
    "error": "错误",
    "valid": "有效",
    "invalid": "无效",
    "draft": "草稿",
    "published": "已发布",
    "high": "高",
    "medium": "中",
    "low": "低",
    "critical": "严重",
    "table": "表",
    "field": "字段",
    "dataset": "数据集",
    "business_domain": "业务域",
    "workflow": "工作流",
    "intent": "意图",
    "agent_shell": "Agent 控制台",
    "context": "上下文",
    "reporting": "报告",
    "delivery": "交付",
    "batch": "批处理",
    "template": "模板",
    "intake": "接入",
    "quality": "质量",
    "knowledge": "知识库",
    "governance": "治理",
    "control_plane": "控制面",
    "not_null": "非空",
    "unique": "唯一",
    "format": "格式",
    "range": "范围",
    "enum": "枚举",
    "cross_field": "跨字段",
    "field_level": "字段级",
    "domain_aware": "领域感知",
    "proposed": "待确认",
    "accepted": "已接受",
    "in_progress": "处理中",
    "blocked": "阻塞",
    "completed": "已完成",
    "dropped": "已放弃",
    "accept": "接受",
    "reject": "拒绝",
    "edit": "编辑",
    "manual_review": "人工复核",
}


def format_value(value: object | None) -> str:
    """Convert a Python value into a compact UI-friendly string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, Real) and not isinstance(value, bool):
        numeric_value = float(value)
        if isinstance(value, int) or numeric_value.is_integer():
            return str(int(numeric_value))
        return f"{numeric_value:.2f}"
    if isinstance(value, str):
        text = value.strip()
        return DISPLAY_VALUE_LABELS.get(text, text)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            formatted_item = format_value(item)
            if formatted_item:
                parts.append(f"{key}={formatted_item}")
        return "; ".join(parts)
    if isinstance(value, (list, tuple, set)):
        items = [format_value(item) for item in value]
        items = [item for item in items if item]
        return ", ".join(items)
    return str(value)
