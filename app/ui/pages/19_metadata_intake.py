"""Streamlit page for enterprise metadata intake adapters."""

import streamlit as st

from app.core.intake.intake_adapter_service import IntakeAdapterService
from app.core.intake.intake_profile_loader import list_enabled_intake_template_profiles


st.title("Enterprise Metadata Intake")
st.caption("Diagnose structured metadata templates and normalize them into standard input.")

profiles = list_enabled_intake_template_profiles()
profile_options = ["auto_match"] + [profile.profile_name for profile in profiles]

st.subheader("Available Intake Profiles")
st.dataframe([profile.model_dump() for profile in profiles], use_container_width=True)

st.subheader("Diagnose & Normalize")
file_path = st.text_input("Metadata file path")
sheet_name = st.text_input("Sheet name (optional)")
selected_profile = st.selectbox("Intake profile", profile_options)

service = IntakeAdapterService()

if st.button("Diagnose Template"):
    if not file_path:
        st.warning("Please provide a metadata file path first.")
    else:
        result = service.diagnose_intake_template(file_path, sheet_name=sheet_name or None)
        st.json(result.model_dump())

if st.button("Normalize Input"):
    if not file_path:
        st.warning("Please provide a metadata file path first.")
    else:
        profile_name = None if selected_profile == "auto_match" else selected_profile
        result = service.normalize_metadata_input(
            file_path,
            profile_name=profile_name,
            sheet_name=sheet_name or None,
        )
        st.json(result.model_dump())
        if result.status == "success":
            st.success(
                f"Normalized {result.row_count} rows across {result.table_count} tables."
            )

