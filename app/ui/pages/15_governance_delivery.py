"""Governance delivery package page."""

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

from app.core.delivery.delivery_service import DeliveryService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_delivery_package_with_review_from_file,
)
from app.ui.page_overview import build_workflow_overview
from app.ui.performance_helpers import render_json_section, render_records_dataframe_section
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import render_key_value_block, render_page_header

initialize_session_state()

render_page_header(
    "Governance Delivery",
    "Build confirmation workbooks and a local governance delivery package.",
)

uploaded_file_path = get_current_input_file_path()
current_result: WorkflowResult | None = get_workflow_result()
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
                    set_workflow_result_state(current_result)
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
                    set_workflow_result_state(current_result)
            except Exception as exc:
                st.error(f"Failed to build delivery package: {exc}")
            else:
                st.success("Governance delivery package generated.")

result: WorkflowResult | None = get_workflow_result()
if result is None:
    st.info("Build a delivery package to see generated artifact paths.")
    st.stop()

render_result_overview(
    build_workflow_overview(
        result,
        title="交付总览",
        next_step="先看交付物，再下载 workbook 或 manifest。",
    )
)

st.subheader("Generated Workbooks")
if result.confirmation_workbook_results:
    render_records_dataframe_section(
        "Generated Workbooks",
        result.confirmation_workbook_results,
        key_prefix="delivery_workbooks",
    )
else:
    st.info("No confirmation workbooks have been generated yet.")

st.subheader("Delivery Package")
if result.governance_delivery_package_result is not None:
    package_result = result.governance_delivery_package_result
    render_key_value_block(
        None,
        rows=[("Output directory", package_result.output_dir)],
    )
    render_json_section("Generated Files", package_result.generated_files, compact=True)
else:
    st.info("No delivery package has been generated yet.")

st.subheader("Manifest Preview")
if result.governance_delivery_manifest is not None:
    render_json_section("Manifest Preview", result.governance_delivery_manifest, compact=True)
else:
    st.info("Manifest will appear after building the delivery package.")

