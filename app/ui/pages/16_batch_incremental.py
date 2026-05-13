"""Batch processing and incremental rerun page."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.reports.report_service import export_all_reports
from app.core.utils.file_utils import save_uploaded_file

initialize_session_state()

st.title("Batch & Incremental Rerun")
st.write("Run multi-file governance batches and changed-only reruns from local snapshots.")

uploaded_files = st.file_uploader(
    "Choose metadata files",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
)
group_by = st.selectbox(
    "Group by",
    options=["system_name", "schema_name", "domain_hint"],
)
batch_name = st.text_input("Batch name", value="default_batch_governance")
upload_dir = PROJECT_ROOT / "outputs" / "batch_uploads"

if uploaded_files:
    saved_paths = [
        save_uploaded_file(uploaded_file, upload_dir)
        for uploaded_file in uploaded_files
    ]
    st.session_state["batch_file_paths"] = saved_paths
    st.success(f"Saved {len(saved_paths)} files for batch processing.")

file_paths = st.session_state.get("batch_file_paths", [])
st.write(f"Selected files: {len(file_paths)}")

engine = WorkflowEngine()
col_full, col_incremental, col_export = st.columns(3)

with col_full:
    if st.button("Full Batch Run", type="primary"):
        if not file_paths:
            st.warning("Upload one or more metadata files first.")
        else:
            with st.spinner("Running full batch governance..."):
                result = engine.run_batch_governance_workflow(
                    file_paths=file_paths,
                    group_by=group_by,
                    changed_only=False,
                    batch_name=batch_name,
                )
            st.session_state["workflow_result"] = result
            st.success("Batch governance run completed.")

with col_incremental:
    if st.button("Changed-Only Rerun"):
        if not file_paths:
            st.warning("Upload one or more metadata files first.")
        else:
            with st.spinner("Running changed-only rerun..."):
                result = engine.run_batch_governance_workflow(
                    file_paths=file_paths,
                    group_by=group_by,
                    changed_only=True,
                    batch_name=batch_name,
                )
            st.session_state["workflow_result"] = result
            st.success("Changed-only rerun completed.")

with col_export:
    if st.button("Export Batch Report"):
        result = st.session_state.get("workflow_result")
        if result is None:
            st.warning("Run a batch first.")
        else:
            paths = export_all_reports(
                result,
                str(PROJECT_ROOT / "outputs" / "reports"),
                f"{batch_name}_batch_report",
            )
            st.success(f"Batch report exported: {paths['json']}")

result = st.session_state.get("workflow_result")
if result is None:
    st.info("Run a batch to see summaries.")
    st.stop()

st.subheader("Batch Group Summary")
if result.batch_group_results:
    st.dataframe(
        [group.model_dump() for group in result.batch_group_results],
        use_container_width=True,
    )
else:
    st.info("No batch groups were processed.")

st.subheader("Incremental Diff Summary")
if result.incremental_diff_summary is not None:
    st.json(result.incremental_diff_summary.model_dump())
else:
    st.info("No diff summary is available.")

st.subheader("Diff Items")
if result.incremental_diff_items:
    st.dataframe(
        [item.model_dump() for item in result.incremental_diff_items],
        use_container_width=True,
    )
else:
    st.info("No diff items are available.")

st.subheader("Rerun Scope Summary")
st.json(result.rerun_scope_summary or {})

