"""Confirmation workbook import page."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    get_confirmation_import_file_path,
    get_confirmation_template_diagnosis,
    get_confirmation_validation_result,
    ensure_project_root_on_path,
    get_workflow_result,
    initialize_session_state,
    set_confirmation_import_file_path,
    set_confirmation_template_diagnosis,
    set_confirmation_validation_result,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.delivery.confirmation_template_loader import (
    list_enabled_confirmation_template_profiles,
)
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.utils.file_utils import save_uploaded_file
from app.ui.performance_helpers import render_json_section, render_records_dataframe_section
from app.ui.status_blocks import render_page_header
from app.ui.workbench_cache import (
    diagnose_confirmation_template_cached,
    file_cache_key,
    validate_confirmation_workbook_cached,
)

initialize_session_state()

render_page_header(
    "Confirmation Import",
    (
        "Validate, diagnose templates, import, merge, and prepare changed-object "
        "rerun scope from filled confirmation workbooks."
    ),
)

uploaded_file = st.file_uploader("Upload confirmation workbook", type=["xlsx", "csv"])
workbook_type = st.selectbox(
    "Workbook type",
    options=[
        "mapping_confirmation",
        "stg_confirmation",
        "quality_rule_confirmation",
        "backlog_confirmation",
    ],
)
template_options = ["auto_match"] + [
    profile.template_name for profile in list_enabled_confirmation_template_profiles()
]
selected_template = st.selectbox("Confirmation template", template_options)

if uploaded_file is not None:
    saved_path = save_uploaded_file(uploaded_file, PROJECT_ROOT / "outputs" / "confirmation_imports")
    set_confirmation_import_file_path(saved_path)
    st.success(f"Workbook saved: {saved_path}")

file_path = get_confirmation_import_file_path()
importer = ConfirmationWorkbookImporter()
engine = WorkflowEngine()

col_validate, col_diagnose, col_import, col_rerun = st.columns(4)
with col_validate:
    if st.button("Validate Workbook"):
        if not file_path:
            st.warning("Upload a confirmation workbook first.")
        else:
            validation = validate_confirmation_workbook_cached(
                file_path,
                workbook_type,
                file_cache_key(file_path),
            )
            set_confirmation_validation_result(validation.model_dump())

with col_diagnose:
    if st.button("Diagnose Confirmation Template"):
        if not file_path:
            st.warning("Upload a confirmation workbook first.")
        else:
            diagnosis = diagnose_confirmation_template_cached(
                file_path,
                workbook_type,
                file_cache_key(file_path),
            )
            set_confirmation_template_diagnosis(diagnosis.model_dump())

with col_import:
    if st.button("Import and Merge", type="primary"):
        if not file_path:
            st.warning("Upload a confirmation workbook first.")
        else:
            template_name = None if selected_template == "auto_match" else selected_template
            result = engine.import_confirmation_with_template(
                file_path,
                template_name=template_name,
                workbook_type=workbook_type,
            )
            set_workflow_result_state(result)
            st.success("Workbook imported and merged.")

with col_rerun:
    if st.button("Import and Rerun Changed Objects"):
        if not file_path:
            st.warning("Upload a confirmation workbook first.")
        else:
            template_name = None if selected_template == "auto_match" else selected_template
            result = engine.import_confirmation_with_template_and_rerun(
                file_path,
                template_name=template_name,
                workbook_type=workbook_type,
                rerun_changed_only=True,
            )
            set_workflow_result_state(result)
            st.success("Workbook imported and rerun scope prepared.")

st.subheader("Validation Result")
confirmation_validation_result = get_confirmation_validation_result()
if confirmation_validation_result:
    render_json_section("Validation Result", confirmation_validation_result)
else:
    st.info("Validate a workbook to see the result.")

st.subheader("Template Diagnosis")
confirmation_template_diagnosis = get_confirmation_template_diagnosis()
if confirmation_template_diagnosis:
    render_json_section("Template Diagnosis", confirmation_template_diagnosis)
else:
    st.info("Diagnose a workbook template to see matched template and mapping evidence.")

result = get_workflow_result()
if result is not None and result.workbook_import_summaries:
    st.subheader("Import Summary")
    render_records_dataframe_section(
        "Import Summary",
        result.workbook_import_summaries,
        key_prefix="confirmation_import_summary",
    )
    st.subheader("Round-Trip Results")
    render_records_dataframe_section(
        "Round-Trip Results",
        result.roundtrip_results,
        key_prefix="confirmation_roundtrip_results",
    )
    st.subheader("Changed Objects Summary")
    render_json_section("Changed Objects Summary", result.roundtrip_changed_objects_summary)
    if result.confirmation_template_match_result:
        st.subheader("Confirmation Template Match")
        render_json_section("Confirmation Template Match", result.confirmation_template_match_result)
    if result.confirmation_template_mapping_result:
        st.subheader("Confirmation Template Mapping")
        render_json_section("Confirmation Template Mapping", result.confirmation_template_mapping_result)
    st.subheader("Rerun Scope")
    render_json_section("Rerun Scope", result.rerun_scope_summary)

