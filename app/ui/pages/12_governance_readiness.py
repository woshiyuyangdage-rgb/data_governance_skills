"""Governance readiness and remediation workbench."""

from datetime import datetime
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

from app.core.governance import GapClassifier, ReadinessAssessor, RemediationPlanner
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import run_full_governance_work_package_from_file
from app.core.utils.result_utils import (
    governance_gaps_to_dataframe,
    governance_work_package_summary_to_dataframe,
    readiness_scores_to_dataframe,
    remediation_actions_to_dataframe,
)

initialize_session_state()

st.title("Governance Readiness")
st.write(
    "Assess governance readiness, classify gaps, and build a remediation work package."
)


def _build_readiness_from_result(result: WorkflowResult) -> WorkflowResult:
    assessor = ReadinessAssessor()
    classifier = GapClassifier()
    planner = RemediationPlanner()
    result.readiness_scores = assessor.assess(result)
    result.governance_gaps = classifier.classify(result)
    result.remediation_actions = planner.build_actions(
        result.readiness_scores,
        result.governance_gaps,
    )
    result.governance_work_package = planner.build_work_package(
        result.readiness_scores,
        result.governance_gaps,
        result.remediation_actions,
        package_name="streamlit_governance_work_package",
    )
    result.readiness_summary = planner.summarize(
        result.readiness_scores,
        result.governance_gaps,
        result.remediation_actions,
    )
    return result


def _filtered_dataframe(
    df: pd.DataFrame,
    column_name: str,
    label: str,
) -> pd.DataFrame:
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

col_run, col_export = st.columns(2)
with col_run:
    if st.button("Run Readiness Assessment", type="primary"):
        if uploaded_file_path:
            try:
                with st.spinner("Running full governance work-package workflow..."):
                    result = run_full_governance_work_package_from_file(uploaded_file_path)
            except Exception as exc:
                st.error(f"Failed to run readiness assessment: {exc}")
            else:
                st.session_state["workflow_result"] = result
                st.session_state["workflow_result_file_path"] = uploaded_file_path
                st.success("Governance readiness assessment completed.")
        elif result is not None:
            result = _build_readiness_from_result(result)
            st.session_state["workflow_result"] = result
            st.success("Governance readiness assessment completed from current result.")
        else:
            st.warning("Run a workflow or upload a metadata file before assessment.")

with col_export:
    if st.button("Export Governance Work Package"):
        current_result: WorkflowResult | None = st.session_state.get("workflow_result")
        if current_result is None or current_result.governance_work_package is None:
            st.warning("Build a governance work package before exporting.")
        else:
            output_dir = PROJECT_ROOT / "outputs" / "governance_work_packages"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"governance_work_package_{timestamp}.json"
            output_path.write_text(
                json.dumps(
                    current_result.governance_work_package.model_dump(),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            st.success(f"Governance work package exported to {output_path}")

result = st.session_state.get("workflow_result")
if result is None:
    st.info("No workflow result is available yet.")
else:
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Readiness Scores", len(result.readiness_scores))
    metric_col2.metric("Governance Gaps", len(result.governance_gaps))
    metric_col3.metric("Remediation Actions", len(result.remediation_actions))
    metric_col4.metric(
        "Work Package",
        result.governance_work_package.package_name
        if result.governance_work_package is not None
        else "not built",
    )

    st.subheader("Work Package Summary")
    summary_df = governance_work_package_summary_to_dataframe(
        result.governance_work_package,
        result.readiness_summary,
    )
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True)
    else:
        st.info("No work package summary is available.")

    st.subheader("Table-Level Readiness")
    readiness_df = readiness_scores_to_dataframe(result.readiness_scores)
    readiness_df = _filtered_dataframe(
        readiness_df,
        "readiness_level",
        "Filter readiness level",
    )
    if not readiness_df.empty:
        st.dataframe(readiness_df, use_container_width=True)
    else:
        st.info("No readiness scores are available.")

    st.subheader("Governance Gaps")
    gaps_df = governance_gaps_to_dataframe(result.governance_gaps)
    gaps_df = _filtered_dataframe(gaps_df, "gap_type", "Filter gap type")
    if not gaps_df.empty:
        st.dataframe(gaps_df, use_container_width=True)
    else:
        st.info("No governance gaps are available.")

    st.subheader("Remediation Actions")
    actions_df = remediation_actions_to_dataframe(result.remediation_actions)
    actions_df = _filtered_dataframe(actions_df, "owner_role", "Filter owner role")
    actions_df = _filtered_dataframe(actions_df, "priority", "Filter priority")
    if not actions_df.empty:
        st.dataframe(actions_df, use_container_width=True)
    else:
        st.info("No remediation actions are available.")

