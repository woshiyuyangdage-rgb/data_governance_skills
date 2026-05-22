"""Diagnosis page for uploaded metadata files."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.page_utils import (
    ensure_agent_shell_session_id,
    get_selected_workflow_profile,
    get_task_response,
    get_uploaded_file_path,
    get_uploaded_file_signature,
    get_workflow_result,
    set_selected_workflow_profile,
    set_task_response_state,
)
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview
from app.ui.performance_helpers import (
    ensure_large_file_runtime_ready,
    render_deferred_dataframe_section,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_page_header

ensure_project_root_on_path()

from app.core.agent.session_store import (
    set_last_exported_files,
    set_last_task_context,
    set_last_uploaded_file,
)
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.orchestrator.task_service import run_governance_task
from app.ui.workbench_cache import (
    issues_to_dataframe,
    mapping_results_to_dataframe,
    quality_rules_to_dataframe,
    review_summary_to_dataframe,
    skill_outputs_to_dataframe,
    stg_fields_to_dataframe,
    stg_tables_to_dataframe,
    tasks_to_dataframe,
    unmapped_fields_to_dataframe,
)

initialize_session_state()

render_page_header(
    "Diagnosis Workbench",
    (
        "Select a workflow profile, run the unified governance task entrypoint, then "
        "inspect or review the returned results."
    ),
    info=(
        "Prefer a natural-language or preview-first entry? Use the Intent Runner or "
        "Agent Shell page before running a workflow directly here."
    ),
)

uploaded_file_path = get_uploaded_file_path()
if not uploaded_file_path:
    st.warning("No metadata file is available yet. Please upload a CSV or Excel file first.")
else:
    ensure_large_file_runtime_ready(
        uploaded_file_path,
        get_uploaded_file_signature(),
    )
    agent_session_id = ensure_agent_shell_session_id()
    set_last_uploaded_file(agent_session_id, uploaded_file_path)

    enabled_profiles = list_enabled_profiles()
    profile_lookup = {profile.name: profile for profile in enabled_profiles}
    profile_names = list(profile_lookup.keys())
    selected_profile_name = get_selected_workflow_profile()
    if selected_profile_name not in profile_lookup:
        selected_profile_name = profile_names[0] if profile_names else "metadata_diagnosis_only"
    selected_index = profile_names.index(selected_profile_name) if profile_names else 0

    st.caption(f"Current input file: {uploaded_file_path}")
    selected_profile_name = st.selectbox(
        "Workflow Profile",
        options=profile_names,
        index=selected_index,
        format_func=lambda name: f"{name} - {profile_lookup[name].description}",
    )
    set_selected_workflow_profile(selected_profile_name)
    selected_profile = profile_lookup[selected_profile_name]
    st.caption(
        f"Selected stages: {', '.join(selected_profile.stages)} | "
        f"supports_review_replay={selected_profile.supports_review_replay}"
    )

    with st.expander("Advanced Options", expanded=False):
        export_reports = st.checkbox(
            "Export Reports After Run",
            value=False,
            help="Automatically export JSON / Markdown / Excel files after a successful run.",
        )
        if selected_profile.name in {
            "diagnosis_mapping_stg_with_review",
            "diagnosis_mapping_stg_quality_with_review",
        }:
            apply_review_replay = st.checkbox(
                "Apply Review Replay",
                value=True,
                disabled=True,
                help="This workflow profile always replays saved review overrides.",
            )
        elif selected_profile.supports_review_replay:
            apply_review_replay = st.checkbox(
                "Apply Review Replay",
                value=True,
                help="Replay saved mapping and STG overrides during this run.",
            )
        else:
            apply_review_replay = st.checkbox(
                "Apply Review Replay",
                value=False,
                disabled=True,
                help="This workflow profile does not support review replay.",
            )

    if st.button("Run Pipeline", type="primary"):
        try:
            with st.spinner("Running governance workflow..."):
                task_response = run_governance_task(
                    GovernanceTaskRequest(
                        file_path=uploaded_file_path,
                        profile_name=selected_profile_name,
                        apply_review_replay=apply_review_replay,
                        export_reports=export_reports,
                    )
                )
        except Exception as exc:
            st.error(f"Unexpected error while running diagnosis: {exc}")
        else:
            task_request = GovernanceTaskRequest(
                file_path=uploaded_file_path,
                profile_name=selected_profile_name,
                apply_review_replay=apply_review_replay,
                export_reports=export_reports,
            )
            result = task_response.result
            set_task_response_state(task_response, file_path=uploaded_file_path)
            set_last_task_context(
                agent_session_id,
                task_request=task_request,
                task_response=task_response,
            )
            if task_response.exported_files:
                set_last_exported_files(agent_session_id, task_response.exported_files)
            if task_response.status == "success":
                st.success("Pipeline execution completed.")
            else:
                st.error(task_response.message)

task_response = get_task_response()
result = get_workflow_result()
if result is not None:
    render_result_overview(
        build_workflow_overview(
            result,
            title="诊断结果总览",
            next_step="先看映射、STG 和质量规则建议，再去 Review 页面处理人工确认。",
        )
    )
    if task_response is not None and task_response.exported_files:
        st.info("Reports were exported during the run and are available on the Reports page.")

    with st.expander("Skill Summaries", expanded=False):
        render_deferred_dataframe_section(
            "Skill Summaries",
            lambda: skill_outputs_to_dataframe(result.skill_outputs),
            empty_message="No skill outputs available for display.",
            compact=True,
            key_prefix="diagnosis_skill_summaries",
        )

    with st.expander("Issues", expanded=False):
        render_deferred_dataframe_section(
            "Issues",
            lambda: issues_to_dataframe(result.issues),
            empty_message="No issues were generated.",
            compact=True,
            key_prefix="diagnosis_issues",
        )

    with st.expander("Tasks", expanded=False):
        render_deferred_dataframe_section(
            "Tasks",
            lambda: tasks_to_dataframe(result.tasks),
            empty_message="No tasks were generated.",
            compact=True,
            key_prefix="diagnosis_tasks",
        )

    if result.mapping_results or result.unmapped_fields or result.mapping_summary:
        render_explanation_block(
            "标准映射概览",
            summary=result.mapping_summary or "No mapping summary available.",
            next_step="Review mapping suggestions before confirming or exporting downstream assets.",
        )

        with st.expander("Mapping Results", expanded=False):
            render_deferred_dataframe_section(
                "Mapping Results",
                lambda: mapping_results_to_dataframe(result.mapping_results),
                empty_message="No standard mapping recommendations were generated.",
                compact=True,
                key_prefix="diagnosis_mapping_results",
            )

        with st.expander("Unmapped or Low-Confidence Fields", expanded=False):
            render_deferred_dataframe_section(
                "Unmapped or Low-Confidence Fields",
                lambda: unmapped_fields_to_dataframe(result.unmapped_fields),
                empty_message="No low-confidence or unmapped fields were flagged.",
                compact=True,
                key_prefix="diagnosis_unmapped_fields",
            )

    if result.confirmed_mapping_results:
        with st.expander("Confirmed Mapping Results", expanded=False):
            render_deferred_dataframe_section(
                "Confirmed Mapping Results",
                lambda: mapping_results_to_dataframe(result.confirmed_mapping_results),
                empty_message="No confirmed mapping results are available.",
                compact=True,
                key_prefix="diagnosis_confirmed_mapping",
            )

    if result.stg_suggestions or result.stg_field_suggestions or result.stg_summary:
        render_explanation_block(
            "STG 概览",
            summary=result.stg_summary or "No STG summary available.",
            next_step="Review STG field suggestions before accepting the final structure.",
        )

        with st.expander("STG Table Suggestions", expanded=False):
            render_deferred_dataframe_section(
                "STG Table Suggestions",
                lambda: stg_tables_to_dataframe(result.stg_suggestions),
                empty_message="No STG table suggestions were generated.",
                compact=True,
                key_prefix="diagnosis_stg_tables",
            )

        with st.expander("STG Field Suggestions", expanded=False):
            render_deferred_dataframe_section(
                "STG Field Suggestions",
                lambda: stg_fields_to_dataframe(result.stg_field_suggestions),
                empty_message="No STG field suggestions were generated.",
                columns=[
                    "source_table_name",
                    "source_field_name",
                    "recommended_stg_field_name",
                    "recommended_stg_field_name_cn",
                    "recommended_data_type",
                    "mapping_source",
                    "action",
                    "notes",
                ],
                compact=True,
                key_prefix="diagnosis_stg_fields",
            )

    if result.confirmed_stg_suggestions:
        with st.expander("Confirmed STG Suggestions", expanded=False):
            render_deferred_dataframe_section(
                "Confirmed STG Suggestions",
                lambda: stg_fields_to_dataframe(result.confirmed_stg_suggestions),
                empty_message="No confirmed STG suggestions are available.",
                compact=True,
                key_prefix="diagnosis_confirmed_stg",
            )

    if result.quality_rule_suggestions or result.quality_rule_summary:
        render_explanation_block(
            "质量规则概览",
            summary=result.quality_rule_summary or "No quality rule summary available.",
            next_step="Open the Quality Rules page to confirm, edit, or export the suggested rules.",
        )

        with st.expander("Quality Rule Suggestions", expanded=False):
            render_deferred_dataframe_section(
                "Quality Rule Suggestions",
                lambda: quality_rules_to_dataframe(result.quality_rule_suggestions),
                empty_message="No quality rule recommendations were generated.",
                compact=True,
                key_prefix="diagnosis_quality_rules",
            )

    if result.review_summary is not None:
        with st.expander("Review Summary", expanded=False):
            render_deferred_dataframe_section(
                "Review Summary",
                lambda: review_summary_to_dataframe(result.review_summary),
                empty_message="No review summary is available.",
                compact=True,
                key_prefix="diagnosis_review_summary",
            )

    if result.mapping_results or result.stg_field_suggestions or result.quality_rule_suggestions:
        st.info("Next step: open the Review page to accept, reject, edit, or mark suggestions for manual review.")
