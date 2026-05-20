"""Streamlit page for domain packs and project templates."""

import streamlit as st

from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.templates.project_template_service import ProjectTemplateService
from app.ui.workbench_cache import file_cache_key, match_domain_pack_from_file_cached


st.title("Domain Governance Packs & Project Templates")
st.caption("Rule-based domain defaults and one-click project template execution.")

packs = list_enabled_domain_packs()
templates = list_enabled_project_templates()

st.subheader("Available Domain Packs")
st.dataframe([pack.model_dump() for pack in packs], use_container_width=True)

st.subheader("Available Project Templates")
st.dataframe([template.model_dump() for template in templates], use_container_width=True)

st.subheader("Run Project Template")
file_path = st.text_input("Metadata file path")
template_name = st.selectbox(
    "Project template",
    [template.template_name for template in templates],
)
domain_options = ["auto_match"] + [pack.pack_name for pack in packs]
selected_domain = st.selectbox("Domain pack", domain_options)
output_dir = st.text_input("Output directory (optional)")

if st.button("Auto Match Domain Pack"):
    if not file_path:
        st.warning("Please provide a metadata file path first.")
    else:
        match = match_domain_pack_from_file_cached(file_path, file_cache_key(file_path))
        st.json(match.model_dump())

if st.button("Run Project Template"):
    if not file_path:
        st.warning("Please provide a metadata file path first.")
    else:
        domain_pack_name = None if selected_domain == "auto_match" else selected_domain
        result = ProjectTemplateService().run_project_template(
            template_name=template_name,
            file_path=file_path,
            domain_pack_name=domain_pack_name,
            output_dir=output_dir or None,
        )
        st.success(result.message)
        if result.domain_pack_match:
            st.write("Matched pack")
            st.json(result.domain_pack_match.model_dump())
        if result.project_template_result:
            st.write("Template defaults")
            st.json(result.project_template_result.model_dump())
        if result.governance_delivery_package_result:
            st.write("Generated outputs")
            st.json(result.governance_delivery_package_result.model_dump())

