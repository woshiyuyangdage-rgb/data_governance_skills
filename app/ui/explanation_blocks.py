"""Shared Streamlit helpers for consistent recommendation explanations."""

from collections.abc import Mapping, Sequence

import streamlit as st

from app.ui.value_formatters import format_value


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
        formatted_value = format_value(value)
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
