"""Governance backlog tracking page."""

import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

import app.core.governance.backlog_store as backlog_store
from app.core.governance.backlog_tracking_service import GovernanceBacklogTrackingService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import run_full_governance_backlog_package_from_file
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview
from app.ui.workbench_cache import (
    backlog_summary_to_dataframe,
    governance_backlog_items_to_dataframe,
)

initialize_session_state()

st.title("Governance Backlog")
st.write("Build, persist, filter, and update local governance backlog items.")


def _filter_df(df: pd.DataFrame, column_name: str, label: str) -> pd.DataFrame:
    if df.empty or column_name not in df.columns:
        return df
    options = sorted(str(value) for value in df[column_name].dropna().unique())
    selected = st.multiselect(label, options=options)
    if not selected:
        return df
    return df[df[column_name].astype(str).isin(selected)]


result: WorkflowResult | None = st.session_state.get("workflow_result")
uploaded_file_path = st.session_state.get("workflow_result_file_path") or st.session_state.get(
    "uploaded_file_path"
)
service = GovernanceBacklogTrackingService()

col_build, col_persist, col_export = st.columns(3)
with col_build:
    if st.button("Build Governance Backlog", type="primary"):
        if uploaded_file_path:
            try:
                with st.spinner("Running full backlog workflow..."):
                    result = run_full_governance_backlog_package_from_file(uploaded_file_path)
            except Exception as exc:
                st.error(f"Failed to build backlog: {exc}")
            else:
                st.session_state["workflow_result"] = result
                st.session_state["workflow_result_file_path"] = uploaded_file_path
                st.success("Governance backlog was built.")
        elif result is not None:
            items, summary = service.build_backlog_from_work_package(
                workflow_result=result
            )
            result.governance_backlog_items = items
            result.backlog_summary = summary
            st.session_state["workflow_result"] = result
            st.success("Governance backlog was built from current result.")
        else:
            st.warning("Run readiness/remediation first or provide an uploaded file.")

with col_persist:
    if st.button("Persist Backlog"):
        current_result: WorkflowResult | None = st.session_state.get("workflow_result")
        if current_result is None or not current_result.governance_backlog_items:
            st.warning("Build backlog items before persisting.")
        else:
            save_result = service.persist_backlog_items(
                current_result.governance_backlog_items,
                append=True,
            )
            st.success(f"Persisted {save_result['saved_count']} backlog items.")

with col_export:
    if st.button("Export Backlog JSON"):
        items = backlog_store.list_backlog_items()
        summary = service.summarize_backlog(items)
        output_dir = PROJECT_ROOT / "outputs" / "governance_backlog"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "governance_backlog_export.json"
        output_path.write_text(
            json.dumps(
                {
                    "items": [item.model_dump() for item in items],
                    "summary": summary.model_dump(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        st.success(f"Backlog exported to {output_path}")

persisted_items = backlog_store.list_backlog_items()
current_items = (
    result.governance_backlog_items if result is not None and result.governance_backlog_items else []
)
display_items = persisted_items or current_items
summary = service.summarize_backlog(display_items)

if result is not None:
    render_result_overview(
        build_workflow_overview(
            result,
            title="治理待办总览",
            next_step="先确认待办，再做持久化或状态更新。",
        )
    )

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Backlog Items", summary.total_items)
metric_col2.metric("Blocked", summary.blocked_count)
metric_col3.metric("Completed", summary.completed_count)
metric_col4.metric("Owners", len(summary.by_owner_role))

st.subheader("Backlog Summary")
summary_df = backlog_summary_to_dataframe(summary)
if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True)

st.subheader("Backlog Items")
items_df = governance_backlog_items_to_dataframe(display_items)
items_df = _filter_df(items_df, "status", "Filter status")
items_df = _filter_df(items_df, "priority", "Filter priority")
items_df = _filter_df(items_df, "owner_role", "Filter owner role")
items_df = _filter_df(items_df, "gap_type", "Filter gap type")
if not items_df.empty:
    st.dataframe(items_df, use_container_width=True)
else:
    st.info("No backlog items are available.")

st.subheader("Update Backlog Status")
if display_items:
    backlog_lookup = {item.backlog_id: item for item in display_items}
    selected_id = st.selectbox("Backlog item", options=sorted(backlog_lookup))
    new_status = st.selectbox(
        "New status",
        options=["proposed", "accepted", "in_progress", "blocked", "completed", "dropped"],
    )
    note = st.text_input("Update note", value="")
    if st.button("Update Status"):
        result_update = service.update_backlog_status(
            selected_id,
            new_status,
            note=note or None,
        )
        if result_update.status == "success":
            st.success(result_update.message)
        else:
            st.error(result_update.message)
else:
    st.info("Persist backlog items before updating status.")
