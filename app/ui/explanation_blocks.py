"""Shared Streamlit helpers for consistent recommendation explanations."""

from collections.abc import Mapping, Sequence
from numbers import Real

import streamlit as st


def _format_value(value: object | None) -> str:
    """Convert a Python value into a compact UI-friendly string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
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
            formatted_item = _format_value(item)
            if formatted_item:
                parts.append(f"{key}={formatted_item}")
        return "; ".join(parts)
    if isinstance(value, (list, tuple, set)):
        items = [_format_value(item) for item in value]
        items = [item for item in items if item]
        return ", ".join(items)
    return str(value)


def render_explanation_block(
    title: str,
    *,
    summary: str | None = None,
    details: Mapping[str, object | None] | Sequence[tuple[str, object | None]] | None = None,
    reason: str | None = None,
    evidence: Sequence[str] | None = None,
    confidence: float | None = None,
    next_step: str | None = None,
) -> None:
    """Render a compact explanation block with shared section labels."""
    st.subheader(title)
    if summary:
        st.caption(summary)

    rows = list(details.items()) if isinstance(details, Mapping) else list(details or [])
    for label, value in rows:
        formatted_value = _format_value(value)
        if formatted_value:
            st.write(f"- **{label}**: `{formatted_value}`")

    if confidence is not None:
        st.write(f"- **置信度**: `{confidence:.2f}`")

    if reason:
        st.markdown("**推荐原因**")
        st.write(reason)

    if evidence:
        st.markdown("**证据**")
        for item in evidence:
            if item:
                st.write(f"- {item}")

    if next_step:
        st.info(next_step)
