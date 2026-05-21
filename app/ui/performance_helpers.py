"""Streamlit helpers for warming heavy caches and rendering large tables lazily."""

from __future__ import annotations

from contextlib import contextmanager

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
    if st.session_state.get(LARGE_FILE_RUNTIME_WARMUP_KEY) == signature:
        cached_result = st.session_state.get(LARGE_FILE_RUNTIME_WARMUP_RESULT_KEY)
        return cached_result if isinstance(cached_result, dict) else {}

    with _runtime_status("Warming large-file runtime") as status:
        if status is not None and hasattr(status, "write"):
            status.write("Caching metadata parser results")
        load_metadata_file_cached(file_path, signature)

        if status is not None and hasattr(status, "write"):
            status.write("Warming semantic mapping index")
        semantic_ready = True
        if semantic_index_enabled():
            semantic_ready = warm_semantic_mapping_index()

        if status is not None and hasattr(status, "write"):
            status.write("Warming quality-rule learning cache")
        quality_ready = True
        if association_rule_learning_enabled():
            load_quality_rule_associations()

        result = {
            "metadata_parser_ready": True,
            "semantic_index_ready": semantic_ready,
            "quality_rule_learning_ready": quality_ready,
        }
        if status is not None and hasattr(status, "update"):
            status.update(label="Large-file runtime ready", state="complete")

    st.session_state[LARGE_FILE_RUNTIME_WARMUP_KEY] = signature
    st.session_state[LARGE_FILE_RUNTIME_WARMUP_RESULT_KEY] = result
    return result


def _subset_dataframe(dataframe: pd.DataFrame, columns: list[str] | None) -> pd.DataFrame:
    if not columns:
        return dataframe
    available_columns = [column for column in columns if column in dataframe.columns]
    if not available_columns:
        return dataframe
    return dataframe.loc[:, available_columns]


def render_lazy_dataframe_section(
    title: str,
    dataframe: pd.DataFrame,
    *,
    empty_message: str = "No records available.",
    preview_rows: int = 25,
    render_limit: int = 120,
    columns: list[str] | None = None,
    compact: bool = False,
    key_prefix: str | None = None,
) -> None:
    """Render a dataframe with a preview first and full table on demand."""
    dataframe = _subset_dataframe(dataframe, columns)
    row_count = len(dataframe)

    if not compact:
        st.subheader(title)

    if row_count == 0:
        st.info(empty_message)
        return

    if row_count <= render_limit:
        st.dataframe(dataframe, use_container_width=True)
        return

    preview_count = min(preview_rows, row_count)
    st.caption(f"Showing first {preview_count} of {row_count} rows.")
    st.dataframe(dataframe.head(preview_count), use_container_width=True)
    st.caption("The full table stays hidden until you choose to load it.")

    load_key = key_prefix or title
    if st.checkbox("Load full table", key=f"{load_key}_load_full"):
        st.dataframe(dataframe, use_container_width=True)

