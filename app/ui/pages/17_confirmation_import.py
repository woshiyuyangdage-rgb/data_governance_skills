"""Confirmation workbook import page."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.delivery.confirmation_template_loader import (
    list_enabled_confirmation_template_profiles,
)
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.utils.file_utils import save_uploaded_file

initialize_session_state()

st.title("Confirmation Import")
st.write("Validate, diagnose templates, import, merge, and prepare changed-object rerun scope from filled confirmation workbooks.")

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
    st.session_state["confirmation_import_file_path"] = saved_path
    st.success(f"Workbook saved: {saved_path}")

file_path = st.session_state.get("confirmation_import_file_path")
importer = ConfirmationWorkbookImporter()
engine = WorkflowEngine()

col_validate, col_diagnose, col_import, col_rerun = st.columns(4)
with col_validate:
    if st.button("Validate Workbook"):
        if not file_path:
            st.warning("Upload a confirmation workbook first.")
        else:
            validation = importer.validate_workbook(file_path, workbook_type)
            st.session_state["confirmation_validation_result"] = validation.model_dump()

with col_diagnose:
    if st.button("Diagnose Confirmation Template"):
        if not file_path:
            st.warning("Upload a confirmation workbook first.")
        else:
            diagnosis = importer.diagnose_confirmation_template(file_path, workbook_type)
            st.session_state["confirmation_template_diagnosis"] = diagnosis.model_dump()

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
            st.session_state["workflow_result"] = result
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
            st.session_state["workflow_result"] = result
            st.success("Workbook imported and rerun scope prepared.")

st.subheader("Validation Result")
if st.session_state.get("confirmation_validation_result"):
    st.json(st.session_state["confirmation_validation_result"])
else:
    st.info("Validate a workbook to see the result.")

st.subheader("Template Diagnosis")
if st.session_state.get("confirmation_template_diagnosis"):
    st.json(st.session_state["confirmation_template_diagnosis"])
else:
    st.info("Diagnose a workbook template to see matched template and mapping evidence.")

result = st.session_state.get("workflow_result")
if result is not None and result.workbook_import_summaries:
    st.subheader("Import Summary")
    st.dataframe(
        [summary.model_dump() for summary in result.workbook_import_summaries],
        use_container_width=True,
    )
    st.subheader("Round-Trip Results")
    st.dataframe(
        [roundtrip.model_dump() for roundtrip in result.roundtrip_results],
        use_container_width=True,
    )
    st.subheader("Changed Objects Summary")
    st.json(result.roundtrip_changed_objects_summary or {})
    if result.confirmation_template_match_result:
        st.subheader("Confirmation Template Match")
        st.json(result.confirmation_template_match_result.model_dump())
    if result.confirmation_template_mapping_result:
        st.subheader("Confirmation Template Mapping")
        st.json(result.confirmation_template_mapping_result.model_dump())
    st.subheader("Rerun Scope")
    st.json(result.rerun_scope_summary or {})

