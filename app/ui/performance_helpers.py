"""Streamlit helpers for warming heavy caches and rendering large tables lazily."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
    association_rule_learning_enabled,
    load_quality_rule_associations,
)
from app.core.skills.data_standard_mapping_skill.semantic_index import (
    semantic_index_enabled,
    warm_semantic_mapping_index,
)
from app.ui.column_labels import localize_dataframe_columns
from app.ui.page_utils import get_session_value, set_session_value
from app.ui.value_formatters import format_value
from app.ui.workbench_cache import file_cache_key, load_metadata_file_cached

LARGE_FILE_RUNTIME_WARMUP_KEY = "large_file_runtime_warmup_signature"
LARGE_FILE_RUNTIME_WARMUP_RESULT_KEY = "large_file_runtime_warmup_result"


@contextmanager
def _runtime_status(title: str):
    if hasattr(st, "status"):
        with st.status(title, expanded=False) as status:
            yield status
        return

    with st.spinner(title):
        yield None


def _normalize_signature(file_path: str | None, file_signature: str | None) -> str:
    if file_signature:
        return file_signature
    return file_cache_key(file_path)


def ensure_large_file_runtime_ready(
    file_path: str | None,
    file_signature: str | None = None,
) -> dict[str, bool]:
    """Warm the file parser, semantic index, and quality-learning cache once per file."""
    if not file_path:
        return {}

    signature = _normalize_signature(file_path, file_signature)
    if get_session_value(LARGE_FILE_RUNTIME_WARMUP_KEY) == signature:
        cached_result = get_session_value(LARGE_FILE_RUNTIME_WARMUP_RESULT_KEY)
        return cached_result if isinstance(cached_result, dict) else {}

    with _runtime_status("正在准备大文件运行环境") as status:
        if status is not None and hasattr(status, "write"):
            status.write("正在缓存元数据解析结果")
        load_metadata_file_cached(file_path, signature)

        if status is not None and hasattr(status, "write"):
            status.write("正在预热语义映射索引")
        semantic_ready = True
        if semantic_index_enabled():
            semantic_ready = warm_semantic_mapping_index()

        if status is not None and hasattr(status, "write"):
            status.write("正在预热质量规则学习缓存")
        quality_ready = True
        if association_rule_learning_enabled():
            load_quality_rule_associations()

        result = {
            "metadata_parser_ready": True,
            "semantic_index_ready": semantic_ready,
            "quality_rule_learning_ready": quality_ready,
        }
        if status is not None and hasattr(status, "update"):
            status.update(label="大文件运行环境已准备完成", state="complete")

    set_session_value(LARGE_FILE_RUNTIME_WARMUP_KEY, signature)
    set_session_value(LARGE_FILE_RUNTIME_WARMUP_RESULT_KEY, result)
    return result


def _subset_dataframe(dataframe: pd.DataFrame, columns: list[str] | None) -> pd.DataFrame:
    if not columns:
        return dataframe
    available_columns = [column for column in columns if column in dataframe.columns]
    if not available_columns:
        return dataframe
    return dataframe.loc[:, available_columns]


def dataframe_filter_options(dataframe: pd.DataFrame, column_name: str) -> list[str]:
    """Return sorted string filter options for one dataframe column."""
    if dataframe.empty or column_name not in dataframe.columns:
        return []
    return sorted(str(value) for value in dataframe[column_name].dropna().unique())


def filter_dataframe_by_values(
    dataframe: pd.DataFrame,
    column_name: str,
    selected_values: list[str],
) -> pd.DataFrame:
    """Filter a dataframe by string-normalized selected values."""
    if not selected_values or dataframe.empty or column_name not in dataframe.columns:
        return dataframe
    return dataframe[dataframe[column_name].astype(str).isin(selected_values)]


def render_dataframe_multiselect_filter(
    dataframe: pd.DataFrame,
    column_name: str,
    label: str,
) -> pd.DataFrame:
    """Render a multiselect for one dataframe column and return the filtered data."""
    options = dataframe_filter_options(dataframe, column_name)
    if not options:
        return dataframe
    selected = st.multiselect(label, options=options, format_func=format_value)
    return filter_dataframe_by_values(dataframe, column_name, selected)


def json_ready_payload(value: object | None) -> object | None:
    """Convert nested model/dict/list payloads into JSON-friendly values."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return json_ready_payload(value.model_dump())
    if isinstance(value, Mapping):
        return {
            str(key): json_ready_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, set):
        return [json_ready_payload(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [json_ready_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dict__"):
        return json_ready_payload(vars(value))
    return str(value)


def render_json_section(
    title: str,
    value: object | None,
    *,
    empty_message: str = "暂无数据。",
    caption: str | None = None,
    use_expander: bool = False,
    expanded: bool = False,
    compact: bool = False,
) -> None:
    """Render one JSON payload with shared empty-state handling."""
    payload = json_ready_payload(value)

    def _render() -> None:
        if caption:
            st.caption(caption)
        if payload in (None, {}, [], ""):
            st.info(empty_message)
            return
        st.json(payload)

    if use_expander:
        with st.expander(title, expanded=expanded):
            _render()
        return

    if not compact:
        st.subheader(title)
    _render()


def records_to_dataframe(records: Iterable[object]) -> pd.DataFrame:
    """Convert model/dict records into a dataframe for UI rendering."""
    rows: list[Mapping[str, object]] = []
    for record in records:
        if hasattr(record, "model_dump"):
            rows.append(record.model_dump())
        elif isinstance(record, Mapping):
            rows.append(record)
        else:
            rows.append(vars(record))
    return pd.DataFrame(rows)


def render_records_dataframe_section(
    title: str,
    records: Iterable[object],
    *,
    empty_message: str = "暂无记录。",
    key_prefix: str | None = None,
) -> None:
    """Render model/dict records through the lazy dataframe section."""
    dataframe = records_to_dataframe(records)
    render_lazy_dataframe_section(
        title,
        dataframe,
        empty_message=empty_message,
        compact=True,
        key_prefix=key_prefix,
    )


def render_lazy_dataframe_section(
    title: str,
    dataframe: pd.DataFrame,
    *,
    empty_message: str = "暂无记录。",
    preview_rows: int = 25,
    render_limit: int = 120,
    columns: list[str] | None = None,
    compact: bool = False,
    key_prefix: str | None = None,
) -> None:
    """Render a dataframe with a preview first and full table on demand."""
    dataframe = _subset_dataframe(dataframe, columns)
    display_dataframe = localize_dataframe_columns(dataframe)
    row_count = len(dataframe)

    if not compact:
        st.subheader(title)

    if row_count == 0:
        st.info(empty_message)
        return

    if row_count <= render_limit:
        st.dataframe(display_dataframe, use_container_width=True)
        return

    preview_count = min(preview_rows, row_count)
    st.caption(f"仅预览前 {preview_count} 行，共 {row_count} 行。")
    st.dataframe(display_dataframe.head(preview_count), use_container_width=True)
    st.caption("完整表格会在你选择加载后显示，避免大文件页面反复重算。")

    load_key = key_prefix or title
    if st.checkbox("加载完整表格", key=f"{load_key}_load_full"):
        st.dataframe(display_dataframe, use_container_width=True)


def render_deferred_dataframe_section(
    title: str,
    dataframe_builder: Callable[[], pd.DataFrame],
    *,
    empty_message: str = "暂无记录。",
    preview_rows: int = 25,
    render_limit: int = 120,
    columns: list[str] | None = None,
    compact: bool = False,
    key_prefix: str | None = None,
    auto_render: bool = False,
) -> None:
    """Render a dataframe only after the section is opened or explicitly requested."""
    if not compact:
        st.subheader(title)

    load_key = key_prefix or title
    if not auto_render:
        if not st.checkbox("加载表格", key=f"{load_key}_load_deferred"):
            st.caption("表格会在需要查看时再生成，避免大文件页面反复重算。")
            return

    with st.spinner(f"正在生成 {title}..."):
        dataframe = dataframe_builder()

    render_lazy_dataframe_section(
        title,
        dataframe,
        empty_message=empty_message,
        preview_rows=preview_rows,
        render_limit=render_limit,
        columns=columns,
        compact=True,
        key_prefix=key_prefix,
    )
