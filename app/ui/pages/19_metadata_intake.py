"""Streamlit page for enterprise metadata intake adapters."""

import streamlit as st

from app.core.intake.intake_profile_loader import list_enabled_intake_template_profiles
from app.ui.performance_helpers import render_json_section, render_records_dataframe_section
from app.ui.status_blocks import render_page_header
from app.ui.workbench_cache import (
    file_cache_key,
    diagnose_intake_template_cached,
    normalize_metadata_input_cached,
)


render_page_header(
    "Enterprise Metadata Intake",
    caption="Diagnose structured metadata templates and normalize them into standard input.",
)

profiles = list_enabled_intake_template_profiles()
profile_options = ["auto_match"] + [profile.profile_name for profile in profiles]

st.subheader("Available Intake Profiles")
render_records_dataframe_section(
    "Available Intake Profiles",
    profiles,
    key_prefix="intake_profiles",
)

st.subheader("Diagnose & Normalize")
file_path = st.text_input("Metadata file path")
sheet_name = st.text_input("Sheet name (optional)")
selected_profile = st.selectbox("Intake profile", profile_options)

if st.button("Diagnose Template"):
    if not file_path:
        st.warning("Please provide a metadata file path first.")
    else:
        result = diagnose_intake_template_cached(
            file_path,
            sheet_name=sheet_name or None,
            file_signature=file_cache_key(file_path),
        )
        render_json_section("Diagnose Template Result", result)

if st.button("Normalize Input"):
    if not file_path:
        st.warning("Please provide a metadata file path first.")
    else:
        profile_name = None if selected_profile == "auto_match" else selected_profile
        result = normalize_metadata_input_cached(
            file_path,
            profile_name=profile_name,
            sheet_name=sheet_name or None,
            file_signature=file_cache_key(file_path),
        )
        render_json_section("Normalize Input Result", result)
        if result.status == "success":
            st.success(
                f"Normalized {result.row_count} rows across {result.table_count} tables."
            )

