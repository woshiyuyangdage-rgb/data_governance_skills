"""Streamlit page for domain packs and project templates."""

import streamlit as st

from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.templates.project_template_service import ProjectTemplateService
from app.ui.performance_helpers import render_json_section, render_records_dataframe_section
from app.ui.status_blocks import render_page_header
from app.ui.workbench_cache import file_cache_key, match_domain_pack_from_file_cached


render_page_header(
    "领域治理包与项目模板",
    caption="基于规则的领域默认值和一键项目模板执行。",
)

packs = list_enabled_domain_packs()
templates = list_enabled_project_templates()
DOMAIN_OPTION_LABELS = {
    "auto_match": "自动匹配",
}

st.subheader("可用领域治理包")
render_records_dataframe_section(
    "可用领域治理包",
    packs,
    key_prefix="domain_packs",
)

st.subheader("可用项目模板")
render_records_dataframe_section(
    "可用项目模板",
    templates,
    key_prefix="project_templates",
)

st.subheader("运行项目模板")
file_path = st.text_input("元数据文件路径")
template_name = st.selectbox(
    "项目模板",
    [template.template_name for template in templates],
)
domain_options = ["auto_match"] + [pack.pack_name for pack in packs]
selected_domain = st.selectbox(
    "领域治理包",
    domain_options,
    format_func=lambda value: DOMAIN_OPTION_LABELS.get(value, value),
)
output_dir = st.text_input("输出目录（可选）")

if st.button("自动匹配领域治理包"):
    if not file_path:
        st.warning("请先提供元数据文件路径。")
    else:
        match = match_domain_pack_from_file_cached(file_path, file_cache_key(file_path))
        render_json_section("领域治理包匹配", match)

if st.button("运行项目模板"):
    if not file_path:
        st.warning("请先提供元数据文件路径。")
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
            render_json_section("匹配到的治理包", result.domain_pack_match, compact=True)
        if result.project_template_result:
            render_json_section("模板默认值", result.project_template_result, compact=True)
        if result.governance_delivery_package_result:
            render_json_section(
                "生成结果",
                result.governance_delivery_package_result,
                compact=True,
            )

