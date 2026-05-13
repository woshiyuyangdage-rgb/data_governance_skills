"""Governance portfolio and progress page."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.governance.backlog_sla_calculator import BacklogSlaCalculator
from app.core.governance.portfolio_aggregator import GovernancePortfolioAggregator
from app.core.governance.progress_snapshot_service import ProgressSnapshotService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_portfolio_package_from_file,
)
from app.core.reports.report_service import export_all_reports
from app.core.utils.result_utils import (
    backlog_sla_statuses_to_dataframe,
    governance_backlog_items_to_dataframe,
    governance_portfolio_summary_to_dataframe,
    progress_snapshot_to_dataframe,
)

initialize_session_state()

st.title("Governance Portfolio")
st.write("Assess backlog SLA, portfolio workload, overdue risk, and progress snapshots.")


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
snapshot_service = ProgressSnapshotService()

col_run, col_save, col_export = st.columns(3)
with col_run:
    if st.button("Run Portfolio Assessment", type="primary"):
        if uploaded_file_path:
            try:
                with st.spinner("Running governance portfolio workflow..."):
                    result = run_full_governance_portfolio_package_from_file(
                        uploaded_file_path
                    )
            except Exception as exc:
                st.error(f"Failed to assess portfolio: {exc}")
            else:
                st.session_state["workflow_result"] = result
                st.session_state["workflow_result_file_path"] = uploaded_file_path
                st.success("Governance portfolio assessment completed.")
        elif result is not None and result.governance_backlog_items:
            result.backlog_sla_statuses = BacklogSlaCalculator().calculate(
                result.governance_backlog_items
            )
            result.governance_portfolio_summary = GovernancePortfolioAggregator().summarize(
                result.governance_backlog_items,
                readiness_scores=result.readiness_scores,
                backlog_sla_statuses=result.backlog_sla_statuses,
            )
            result.progress_snapshot = snapshot_service.build_progress_snapshot(
                result.governance_backlog_items,
                backlog_sla_statuses=result.backlog_sla_statuses,
                readiness_scores=result.readiness_scores,
            )
            st.session_state["workflow_result"] = result
            st.success("Governance portfolio assessment completed from current result.")
        else:
            st.warning("Build backlog items first or provide an uploaded metadata file.")

with col_save:
    if st.button("Save Progress Snapshot"):
        current_result: WorkflowResult | None = st.session_state.get("workflow_result")
        if current_result is None or current_result.progress_snapshot is None:
            st.warning("Run portfolio assessment before saving a snapshot.")
        else:
            save_result = snapshot_service.save_progress_snapshot(
                current_result.progress_snapshot
            )
            st.success(f"Snapshot saved: {save_result['snapshot_id']}")

with col_export:
    if st.button("Export Portfolio Report"):
        current_result: WorkflowResult | None = st.session_state.get("workflow_result")
        if current_result is None:
            st.warning("Run portfolio assessment before exporting.")
        else:
            output_dir = PROJECT_ROOT / "outputs" / "reports"
            paths = export_all_reports(
                current_result,
                str(output_dir),
                "governance_portfolio_report",
            )
            st.success(f"Portfolio report exported: {paths['json']}")

current_result = st.session_state.get("workflow_result")
if current_result is None:
    st.info("Run a portfolio assessment to populate this page.")
    st.stop()

summary = current_result.governance_portfolio_summary
snapshot = current_result.progress_snapshot

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Backlog Items", summary.total_items if summary else 0)
metric_col2.metric("Overdue", summary.overdue_count if summary else 0)
metric_col3.metric("Blocked", summary.blocked_count if summary else 0)
metric_col4.metric("Owners", len(summary.owner_workload) if summary else 0)

st.subheader("Governance Portfolio Summary")
summary_df = governance_portfolio_summary_to_dataframe(summary)
if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True)

st.subheader("Progress Snapshot")
snapshot_df = progress_snapshot_to_dataframe(snapshot)
if not snapshot_df.empty:
    st.dataframe(snapshot_df, use_container_width=True)

st.subheader("Backlog SLA Status")
sla_df = backlog_sla_statuses_to_dataframe(current_result.backlog_sla_statuses)
if not sla_df.empty:
    st.dataframe(sla_df, use_container_width=True)
else:
    st.info("No SLA status is available.")

st.subheader("Backlog Items")
items_df = governance_backlog_items_to_dataframe(current_result.governance_backlog_items)
sla_lookup = {
    status.backlog_id: status.model_dump()
    for status in current_result.backlog_sla_statuses
}
if not items_df.empty:
    items_df["sla_status"] = items_df["backlog_id"].map(
        lambda value: sla_lookup.get(value, {}).get("sla_status")
    )
    items_df["is_overdue"] = items_df["backlog_id"].map(
        lambda value: sla_lookup.get(value, {}).get("is_overdue", False)
    )
    items_df = _filter_df(items_df, "owner_role", "Filter owner role")
    items_df = _filter_df(items_df, "priority", "Filter priority")
    items_df = _filter_df(items_df, "status", "Filter status")
    overdue_only = st.checkbox("Overdue only")
    if overdue_only:
        items_df = items_df[items_df["is_overdue"] == True]
    st.dataframe(items_df, use_container_width=True)
else:
    st.info("No backlog items are available.")

st.subheader("Owner Workload")
if summary is not None and summary.owner_workload:
    workload_df = pd.DataFrame(
        [
            {"owner_role": owner_role, **payload}
            for owner_role, payload in summary.owner_workload.items()
        ]
    )
    st.dataframe(workload_df, use_container_width=True)
else:
    st.info("No owner workload summary is available.")
