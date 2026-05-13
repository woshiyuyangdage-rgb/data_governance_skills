"""Diagnosis page for uploaded metadata files."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.page_utils import ensure_agent_shell_session_id

ensure_project_root_on_path()

from app.core.agent.session_store import (
    set_last_exported_files,
    set_last_task_context,
    set_last_uploaded_file,
)
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.orchestrator.task_service import run_governance_task
from app.core.utils.result_utils import (
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

st.title("Diagnosis Workbench")
st.write(
    "Select a workflow profile, run the unified governance task entrypoint, then "
    "inspect or review the returned results."
)
st.info(
    "Prefer a natural-language or preview-first entry? Use the Intent Runner or Agent Shell page before running a workflow directly here."
)

uploaded_file_path = st.session_state.get("uploaded_file_path")
if not uploaded_file_path:
    st.warning("No metadata file is available yet. Please upload a CSV or Excel file first.")
else:
    agent_session_id = ensure_agent_shell_session_id()
    set_last_uploaded_file(agent_session_id, uploaded_file_path)

    enabled_profiles = list_enabled_profiles()
    profile_lookup = {profile.name: profile for profile in enabled_profiles}
    profile_names = list(profile_lookup.keys())
    selected_profile_name = st.session_state.get("selected_workflow_profile")
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
    st.session_state["selected_workflow_profile"] = selected_profile_name
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
            st.session_state["governance_task_response"] = task_response
            st.session_state["workflow_result"] = result
            st.session_state["workflow_result_file_path"] = uploaded_file_path
            set_last_task_context(
                agent_session_id,
                task_request=task_request,
                task_response=task_response,
            )
            if task_response.exported_files:
                set_last_exported_files(agent_session_id, task_response.exported_files)
                st.session_state["latest_report_paths"] = task_response.exported_files
                history = list(st.session_state.get("report_export_history", []))
                history.append(task_response.exported_files)
                st.session_state["report_export_history"] = history[-10:]
            if task_response.status == "success":
                st.success("Pipeline execution completed.")
            else:
                st.error(task_response.message)

task_response = st.session_state.get("governance_task_response")
result = st.session_state.get("workflow_result")
if result is not None:
    st.subheader("Run Summary")
    if task_response is not None:
        st.write(f"Profile: `{task_response.profile_name}`")
        st.write(f"Stages Executed: `{', '.join(task_response.stages_executed) or 'N/A'}`")
        st.write(f"Status: `{task_response.status}`")
        st.caption(task_response.message)
        if task_response.exported_files:
            st.info("Reports were exported during the run and are available on the Reports page.")
    else:
        st.write(f"Status: `{result.status}`")
        st.caption(result.message)

    metric_status, metric_table, metric_issue, metric_task, metric_mapping, metric_stg, metric_quality = st.columns(7)
    metric_status.metric("Status", result.status)
    metric_table.metric("Input Tables", result.input_table_count)
    metric_issue.metric("Issue Count", result.issue_count)
    metric_task.metric("Task Count", result.task_count)
    metric_mapping.metric("Mapping Count", len(result.mapping_results))
    metric_stg.metric("STG Count", len(result.stg_field_suggestions))
    metric_quality.metric("Quality Rules", len(result.quality_rule_suggestions))

    st.subheader("Skill Summaries")
    skill_df = skill_outputs_to_dataframe(result.skill_outputs)
    if skill_df.empty:
        st.info("No skill outputs available for display.")
    else:
        st.dataframe(skill_df, use_container_width=True)

    st.subheader("Issues")
    issues_df = issues_to_dataframe(result.issues)
    if issues_df.empty:
        st.info("No issues were generated.")
    else:
        st.dataframe(issues_df, use_container_width=True)

    st.subheader("Tasks")
    tasks_df = tasks_to_dataframe(result.tasks)
    if tasks_df.empty:
        st.info("No tasks were generated.")
    else:
        st.dataframe(tasks_df, use_container_width=True)

    if result.mapping_results or result.unmapped_fields or result.mapping_summary:
        st.subheader("Standard Mapping Summary")
        st.caption(result.mapping_summary or "No mapping summary available.")

        mapping_df = mapping_results_to_dataframe(result.mapping_results)
        st.subheader("Mapping Results")
        if mapping_df.empty:
            st.info("No standard mapping recommendations were generated.")
        else:
            st.dataframe(mapping_df, use_container_width=True)

        unmapped_df = unmapped_fields_to_dataframe(result.unmapped_fields)
        st.subheader("Unmapped or Low-Confidence Fields")
        if unmapped_df.empty:
            st.info("No low-confidence or unmapped fields were flagged.")
        else:
            st.dataframe(unmapped_df, use_container_width=True)

    if result.confirmed_mapping_results:
        st.subheader("Confirmed Mapping Results")
        confirmed_mapping_df = mapping_results_to_dataframe(result.confirmed_mapping_results)
        st.dataframe(confirmed_mapping_df, use_container_width=True)

    if result.stg_suggestions or result.stg_field_suggestions or result.stg_summary:
        st.subheader("STG Summary")
        st.caption(result.stg_summary or "No STG summary available.")

        st.subheader("STG Table Suggestions")
        stg_tables_df = stg_tables_to_dataframe(result.stg_suggestions)
        if stg_tables_df.empty:
            st.info("No STG table suggestions were generated.")
        else:
            st.dataframe(stg_tables_df, use_container_width=True)

        st.subheader("STG Field Suggestions")
        stg_fields_df = stg_fields_to_dataframe(result.stg_field_suggestions)
        if stg_fields_df.empty:
            st.info("No STG field suggestions were generated.")
        else:
            st.dataframe(
                stg_fields_df[
                    [
                        "source_table_name",
                        "source_field_name",
                        "recommended_stg_field_name",
                        "recommended_stg_field_name_cn",
                        "recommended_data_type",
                        "mapping_source",
                        "action",
                        "notes",
                    ]
                ],
                use_container_width=True,
            )

    if result.confirmed_stg_suggestions:
        st.subheader("Confirmed STG Suggestions")
        confirmed_stg_df = stg_fields_to_dataframe(result.confirmed_stg_suggestions)
        st.dataframe(confirmed_stg_df, use_container_width=True)

    if result.quality_rule_suggestions or result.quality_rule_summary:
        st.subheader("Quality Rule Summary")
        st.caption(result.quality_rule_summary or "No quality rule summary available.")

        quality_rules_df = quality_rules_to_dataframe(result.quality_rule_suggestions)
        st.subheader("Quality Rule Suggestions")
        if quality_rules_df.empty:
            st.info("No quality rule recommendations were generated.")
        else:
            st.dataframe(quality_rules_df, use_container_width=True)

    if result.review_summary is not None:
        st.subheader("Review Summary")
        review_summary_df = review_summary_to_dataframe(result.review_summary)
        if not review_summary_df.empty:
            st.dataframe(review_summary_df, use_container_width=True)

    if result.mapping_results or result.stg_field_suggestions or result.quality_rule_suggestions:
        st.info("Next step: open the Review page to accept, reject, edit, or mark suggestions for manual review.")
