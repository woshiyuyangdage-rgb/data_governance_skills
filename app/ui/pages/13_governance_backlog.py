"""Governance backlog tracking page."""

import json
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_workflow_result,
    initialize_session_state,
    set_workflow_result_state,
)

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
from app.ui.performance_helpers import (
    render_dataframe_multiselect_filter,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_metric_row, render_page_header

initialize_session_state()

render_page_header(
    "Governance Backlog",
    "Build, persist, filter, and update local governance backlog items.",
)


result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()
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
                set_workflow_result_state(result, file_path=uploaded_file_path)
                st.success("Governance backlog was built.")
        elif result is not None:
            items, summary = service.build_backlog_from_work_package(
                workflow_result=result
            )
            result.governance_backlog_items = items
            result.backlog_summary = summary
            set_workflow_result_state(result)
            st.success("Governance backlog was built from current result.")
        else:
            st.warning("Run readiness/remediation first or provide an uploaded file.")

with col_persist:
    if st.button("Persist Backlog"):
        current_result: WorkflowResult | None = get_workflow_result()
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

render_metric_row(
    [
        ("Backlog Items", summary.total_items),
        ("Blocked", summary.blocked_count),
        ("Completed", summary.completed_count),
        ("Owners", len(summary.by_owner_role)),
    ],
)

st.subheader("Backlog Summary")
summary_df = backlog_summary_to_dataframe(summary)
if not summary_df.empty:
    render_lazy_dataframe_section(
        "Backlog Summary",
        summary_df,
        compact=True,
        key_prefix="backlog_summary",
    )

st.subheader("Backlog Items")
items_df = governance_backlog_items_to_dataframe(display_items)
items_df = render_dataframe_multiselect_filter(items_df, "status", "Filter status")
items_df = render_dataframe_multiselect_filter(items_df, "priority", "Filter priority")
items_df = render_dataframe_multiselect_filter(
    items_df,
    "owner_role",
    "Filter owner role",
)
items_df = render_dataframe_multiselect_filter(items_df, "gap_type", "Filter gap type")
if not items_df.empty:
    render_lazy_dataframe_section(
        "Backlog Items",
        items_df,
        compact=True,
        key_prefix="backlog_items",
    )
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
