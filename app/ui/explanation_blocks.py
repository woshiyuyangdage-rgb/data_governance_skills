"""Shared Streamlit helpers for consistent recommendation explanations."""

from collections.abc import Mapping, Sequence

import streamlit as st

from app.ui.status_blocks import render_key_value_block


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
    render_key_value_block(title, summary=summary, rows=details)

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
