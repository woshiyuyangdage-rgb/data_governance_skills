"""Governance readiness and remediation workbench."""

from datetime import datetime
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

from app.core.governance import GapClassifier, ReadinessAssessor, RemediationPlanner
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import run_full_governance_work_package_from_file
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview
from app.ui.workbench_cache import (
    governance_gaps_to_dataframe,
    governance_work_package_summary_to_dataframe,
    readiness_scores_to_dataframe,
    remediation_actions_to_dataframe,
)
from app.ui.performance_helpers import (
    render_dataframe_multiselect_filter,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_metric_row, render_page_header

initialize_session_state()

render_page_header(
    "Governance Readiness",
    "Assess governance readiness, classify gaps, and build a remediation work package.",
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


result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()

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
                set_workflow_result_state(result, file_path=uploaded_file_path)
                st.success("Governance readiness assessment completed.")
        elif result is not None:
            result = _build_readiness_from_result(result)
            set_workflow_result_state(result)
            st.success("Governance readiness assessment completed from current result.")
        else:
            st.warning("Run a workflow or upload a metadata file before assessment.")

with col_export:
    if st.button("Export Governance Work Package"):
        current_result: WorkflowResult | None = get_workflow_result()
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

result = get_workflow_result()
if result is None:
    st.info("No workflow result is available yet.")
else:
    render_result_overview(
        build_workflow_overview(
            result,
            title="治理就绪总览",
            next_step="先确认缺口和整改动作，再导出工作包。",
        )
    )

    render_metric_row(
        [
            ("Readiness Scores", len(result.readiness_scores)),
            ("Governance Gaps", len(result.governance_gaps)),
            ("Remediation Actions", len(result.remediation_actions)),
            (
                "Work Package",
                result.governance_work_package.package_name
                if result.governance_work_package is not None
                else "not built",
            ),
        ],
    )

    st.subheader("Work Package Summary")
    summary_df = governance_work_package_summary_to_dataframe(
        result.governance_work_package,
        result.readiness_summary,
    )
    if not summary_df.empty:
        render_lazy_dataframe_section(
            "Work Package Summary",
            summary_df,
            compact=True,
            key_prefix="readiness_work_package_summary",
        )
    else:
        st.info("No work package summary is available.")

    st.subheader("Table-Level Readiness")
    readiness_df = readiness_scores_to_dataframe(result.readiness_scores)
    readiness_df = render_dataframe_multiselect_filter(
        readiness_df,
        "readiness_level",
        "Filter readiness level",
    )
    if not readiness_df.empty:
        render_lazy_dataframe_section(
            "Table-Level Readiness",
            readiness_df,
            compact=True,
            key_prefix="readiness_scores",
        )
    else:
        st.info("No readiness scores are available.")

    st.subheader("Governance Gaps")
    gaps_df = governance_gaps_to_dataframe(result.governance_gaps)
    gaps_df = render_dataframe_multiselect_filter(gaps_df, "gap_type", "Filter gap type")
    if not gaps_df.empty:
        render_lazy_dataframe_section(
            "Governance Gaps",
            gaps_df,
            compact=True,
            key_prefix="readiness_gaps",
        )
    else:
        st.info("No governance gaps are available.")

    st.subheader("Remediation Actions")
    actions_df = remediation_actions_to_dataframe(result.remediation_actions)
    actions_df = render_dataframe_multiselect_filter(
        actions_df,
        "owner_role",
        "Filter owner role",
    )
    actions_df = render_dataframe_multiselect_filter(
        actions_df,
        "priority",
        "Filter priority",
    )
    if not actions_df.empty:
        render_lazy_dataframe_section(
            "Remediation Actions",
            actions_df,
            compact=True,
            key_prefix="readiness_actions",
        )
    else:
        st.info("No remediation actions are available.")
