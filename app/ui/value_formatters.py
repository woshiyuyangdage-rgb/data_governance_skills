"""Shared value formatting helpers for Streamlit UI blocks."""

from __future__ import annotations

from numbers import Real


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
        return value.strip()
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
