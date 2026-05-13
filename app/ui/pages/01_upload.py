"""Upload page for local metadata files."""

import hashlib
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    INPUT_TEMPLATE_DOC_PATH,
    SAMPLE_METADATA_PATH,
    UPLOAD_OUTPUT_DIR,
    ensure_agent_shell_session_id,
    ensure_project_root_on_path,
    initialize_session_state,
)

ensure_project_root_on_path()

from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.agent.session_store import set_last_uploaded_file
from app.core.utils.file_utils import get_file_extension, save_uploaded_file

initialize_session_state()

st.title("Upload Metadata")
st.write("Upload a local CSV or Excel file that follows the metadata input template.")

st.subheader("Template Summary")
st.markdown(
    """
    - Supported formats: `csv`, `xlsx`
    - Supported granularity: `table-level only`, `table + field-level`
    - Preferred template: `table + field-level`
    - Main rule: one row represents one field, and table-level information repeats across rows
    - Required column for all files: `table_name`
    - Recommended field-level column: `field_name`
    """
)
st.caption(f"Detailed spec: {INPUT_TEMPLATE_DOC_PATH}")

st.subheader("Available Workflow Profiles")
enabled_profiles = list_enabled_profiles()
for profile in enabled_profiles:
    st.markdown(
        f"- `{profile.name}`: {profile.description} "
        f"(stages: {', '.join(profile.stages)})"
    )

sample_df = pd.read_csv(SAMPLE_METADATA_PATH)
with st.expander("Preview sample_metadata.csv", expanded=True):
    st.dataframe(sample_df, use_container_width=True)
    st.caption(f"Sample file path: {SAMPLE_METADATA_PATH}")
    st.download_button(
        label="Download Sample CSV",
        data=SAMPLE_METADATA_PATH.read_bytes(),
        file_name=SAMPLE_METADATA_PATH.name,
        mime="text/csv",
    )

uploaded_file = st.file_uploader(
    "Select metadata file",
    type=["csv", "xlsx"],
    help="Upload a metadata file for the local P0 diagnosis workflow.",
)

if uploaded_file is not None:
    current_signature = hashlib.md5(uploaded_file.getvalue()).hexdigest()
    saved_path = st.session_state.get("uploaded_file_path")
    should_save = (
        current_signature != st.session_state.get("uploaded_file_signature")
        or not saved_path
        or not Path(saved_path).exists()
    )

    if should_save:
        try:
            saved_path = save_uploaded_file(uploaded_file, UPLOAD_OUTPUT_DIR)
        except Exception as exc:
            st.error(f"Failed to save uploaded file: {exc}")
        else:
            st.session_state["uploaded_file_path"] = saved_path
            st.session_state["uploaded_file_name"] = uploaded_file.name
            st.session_state["uploaded_file_size"] = uploaded_file.size
            st.session_state["uploaded_file_extension"] = get_file_extension(uploaded_file.name)
            st.session_state["uploaded_file_signature"] = current_signature
            st.session_state["workflow_result"] = None
            st.session_state["workflow_result_file_path"] = None
            st.session_state["latest_report_paths"] = {}
            st.success("File uploaded and saved locally.")

file_path = st.session_state.get("uploaded_file_path")
if file_path:
    agent_session_id = ensure_agent_shell_session_id()
    set_last_uploaded_file(agent_session_id, file_path)

    st.subheader("Current Uploaded File")
    file_info_col1, file_info_col2, file_info_col3 = st.columns(3)
    file_info_col1.metric("File Name", st.session_state.get("uploaded_file_name") or "N/A")
    file_info_col2.metric("File Size (bytes)", st.session_state.get("uploaded_file_size") or 0)
    file_info_col3.metric("Extension", st.session_state.get("uploaded_file_extension") or "N/A")
    st.caption(f"Saved local path: {file_path}")
    st.caption(f"Shared agent session: {agent_session_id}")
