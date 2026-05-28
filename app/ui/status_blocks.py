"""Shared helpers for compact status and key-value UI blocks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import streamlit as st

from app.ui.value_formatters import format_value

MetricRowItem = tuple[str, object | None] | tuple[str, object | None, str | None]


def render_page_header(
    title: str,
    description: str | None = None,
    *,
    caption: str | None = None,
    info: str | None = None,
) -> None:
    """Render a page title and its standard intro text."""
    st.title(title)
    if description:
        st.write(description)
    if caption:
        st.caption(caption)
    if info:
        st.info(info)


def render_metric_row(
    metrics: Sequence[MetricRowItem],
    *,
    max_columns: int = 4,
) -> None:
    """Render a responsive metric row with shared value formatting."""
    if not metrics:
        return

    column_count = min(max_columns, len(metrics)) or 1
    columns = st.columns(column_count)
    for index, metric in enumerate(metrics):
        label = metric[0]
        value = metric[1]
        help_text = metric[2] if len(metric) > 2 else None
        columns[index % column_count].metric(
            label,
            format_value(value) or "N/A",
            help=help_text,
        )


def render_bullet_list(
    title: str | None,
    items: Sequence[object | None],
    *,
    empty_message: str = "暂无条目。",
) -> None:
    """Render a short bullet list with consistent empty-state handling."""
    if title is not None:
        st.subheader(title)

    visible_items = [format_value(item) for item in items]
    visible_items = [item for item in visible_items if item]
    if not visible_items:
        st.info(empty_message)
        return

    for item in visible_items:
        st.write(f"- {item}")


def render_key_value_block(
    title: str | None,
    *,
    summary: str | None = None,
    rows: Mapping[str, object | None] | Sequence[tuple[str, object | None]] | None = None,
    empty_message: str = "暂无明细。",
) -> None:
    """Render a consistent key-value block for page summaries."""
    if title is not None:
        st.subheader(title)
    if summary:
        st.caption(summary)

    normalized_rows = list(rows.items()) if isinstance(rows, Mapping) else list(rows or [])
    if not normalized_rows:
        st.info(empty_message)
        return

    for label, value in normalized_rows:
        formatted_value = format_value(value)
        if formatted_value:
            st.write(f"- **{label}**: `{formatted_value}`")
