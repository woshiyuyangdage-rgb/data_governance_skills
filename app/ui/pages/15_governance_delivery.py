"""Governance delivery package page."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.delivery.delivery_service import DeliveryService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_delivery_package_with_review_from_file,
)

initialize_session_state()

st.title("Governance Delivery")
st.write("Build confirmation workbooks and a local governance delivery package.")

uploaded_file_path = st.session_state.get("workflow_result_file_path") or st.session_state.get(
    "uploaded_file_path"
)
current_result: WorkflowResult | None = st.session_state.get("workflow_result")
output_dir = st.text_input(
    "Output directory",
    value=str(PROJECT_ROOT / "outputs" / "delivery_packages"),
)
base_name = st.text_input("Package or workbook base name", value="governance_delivery_package")

service = DeliveryService()
col_workbooks, col_package = st.columns(2)

with col_workbooks:
    if st.button("Build Confirmation Workbooks"):
        if current_result is None and not uploaded_file_path:
            st.warning("Run a workflow first or upload a metadata file.")
        else:
            try:
                with st.spinner("Building confirmation workbooks..."):
                    if current_result is None:
                        current_result = run_full_governance_delivery_package_with_review_from_file(
                            uploaded_file_path
                        )
                    workbook_results = service.build_confirmation_workbooks(
                        current_result,
                        output_dir=output_dir,
                        base_name=base_name,
                    )
                    current_result.confirmation_workbook_results = workbook_results
                    st.session_state["workflow_result"] = current_result
            except Exception as exc:
                st.error(f"Failed to build confirmation workbooks: {exc}")
            else:
                st.success("Confirmation workbooks generated.")

with col_package:
    if st.button("Build Governance Delivery Package", type="primary"):
        if current_result is None and not uploaded_file_path:
            st.warning("Run a workflow first or upload a metadata file.")
        else:
            try:
                with st.spinner("Building governance delivery package..."):
                    if uploaded_file_path:
                        current_result = run_full_governance_delivery_package_with_review_from_file(
                            uploaded_file_path
                        )
                    else:
                        current_result = service.build_governance_delivery_package(
                            current_result,
                            output_dir=output_dir,
                            base_name=base_name,
                        )
                    st.session_state["workflow_result"] = current_result
            except Exception as exc:
                st.error(f"Failed to build delivery package: {exc}")
            else:
                st.success("Governance delivery package generated.")

result: WorkflowResult | None = st.session_state.get("workflow_result")
if result is None:
    st.info("Build a delivery package to see generated artifact paths.")
    st.stop()

st.subheader("Generated Workbooks")
if result.confirmation_workbook_results:
    st.dataframe(
        [workbook.model_dump() for workbook in result.confirmation_workbook_results],
        use_container_width=True,
    )
else:
    st.info("No confirmation workbooks have been generated yet.")

st.subheader("Delivery Package")
if result.governance_delivery_package_result is not None:
    package_result = result.governance_delivery_package_result
    st.write(f"Output directory: `{package_result.output_dir}`")
    st.json(package_result.generated_files)
else:
    st.info("No delivery package has been generated yet.")

st.subheader("Manifest Preview")
if result.governance_delivery_manifest is not None:
    st.json(result.governance_delivery_manifest.model_dump())
else:
    st.info("Manifest will appear after building the delivery package.")

