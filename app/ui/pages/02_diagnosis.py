"""Diagnosis page for uploaded metadata files."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.page_utils import (
    ensure_agent_shell_session_id,
    get_selected_workflow_profile,
    get_task_response,
    get_uploaded_file_path,
    get_uploaded_file_signature,
    get_workflow_result,
    set_selected_workflow_profile,
    set_task_response_state,
)
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview
from app.ui.performance_helpers import (
    ensure_large_file_runtime_ready,
    render_deferred_dataframe_section,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_page_header

ensure_project_root_on_path()

from app.core.agent.session_store import (
    set_last_exported_files,
    set_last_task_context,
    set_last_uploaded_file,
)
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.orchestrator.task_service import run_governance_task
from app.ui.workbench_cache import (
    issues_to_dataframe,
    mapping_results_to_dataframe,
    quality_rules_to_dataframe,
    review_summary_to_dataframe,
    skill_outputs_to_dataframe,
    stg_fields_to_dataframe,
    stg_tables_to_dataframe,
    tasks_to_dataframe,
    unmapped_fields_to_dataframe,
)

initialize_session_state()

render_page_header(
    "诊断工作台",
    (
        "选择工作流方案，运行统一治理任务入口，然后查看诊断、映射、STG 和质量规则结果。"
    ),
)

uploaded_file_path = get_uploaded_file_path()
if not uploaded_file_path:
    st.warning("当前还没有元数据文件，请先上传 CSV 或 Excel 文件。")
else:
    ensure_large_file_runtime_ready(
        uploaded_file_path,
        get_uploaded_file_signature(),
    )
    agent_session_id = ensure_agent_shell_session_id()
    set_last_uploaded_file(agent_session_id, uploaded_file_path)

    enabled_profiles = list_enabled_profiles()
    profile_lookup = {profile.name: profile for profile in enabled_profiles}
    profile_names = list(profile_lookup.keys())
    selected_profile_name = get_selected_workflow_profile()
    if selected_profile_name not in profile_lookup:
        selected_profile_name = profile_names[0] if profile_names else "metadata_diagnosis_only"
    selected_index = profile_names.index(selected_profile_name) if profile_names else 0

    st.caption(f"当前输入文件: {uploaded_file_path}")
    selected_profile_name = st.selectbox(
        "工作流方案",
        options=profile_names,
        index=selected_index,
        format_func=lambda name: f"{name} - {profile_lookup[name].description}",
    )
    set_selected_workflow_profile(selected_profile_name)
    selected_profile = profile_lookup[selected_profile_name]
    st.caption(
        f"已选阶段: {', '.join(selected_profile.stages)} | "
        f"支持评审回放={selected_profile.supports_review_replay}"
    )

    with st.expander("高级选项", expanded=False):
        export_reports = st.checkbox(
            "运行后导出报告",
            value=False,
            help="运行成功后自动导出 JSON / Markdown / Excel 文件。",
        )
        if selected_profile.name in {
            "diagnosis_mapping_stg_with_review",
            "diagnosis_mapping_stg_quality_with_review",
        }:
            apply_review_replay = st.checkbox(
                "应用评审回放",
                value=True,
                disabled=True,
                help="该工作流方案会固定回放已保存的评审覆盖。",
            )
        elif selected_profile.supports_review_replay:
            apply_review_replay = st.checkbox(
                "应用评审回放",
                value=True,
                help="运行时回放已保存的映射和 STG 覆盖。",
            )
        else:
            apply_review_replay = st.checkbox(
                "应用评审回放",
                value=False,
                disabled=True,
                help="该工作流方案不支持评审回放。",
            )

    if st.button("运行流程", type="primary"):
        try:
            with st.spinner("正在运行治理工作流..."):
                task_response = run_governance_task(
                    GovernanceTaskRequest(
                        file_path=uploaded_file_path,
                        profile_name=selected_profile_name,
                        apply_review_replay=apply_review_replay,
                        export_reports=export_reports,
                    )
                )
        except Exception as exc:
            st.error(f"运行诊断时发生异常: {exc}")
        else:
            task_request = GovernanceTaskRequest(
                file_path=uploaded_file_path,
                profile_name=selected_profile_name,
                apply_review_replay=apply_review_replay,
                export_reports=export_reports,
            )
            result = task_response.result
            set_task_response_state(task_response, file_path=uploaded_file_path)
            set_last_task_context(
                agent_session_id,
                task_request=task_request,
                task_response=task_response,
            )
            if task_response.exported_files:
                set_last_exported_files(agent_session_id, task_response.exported_files)
            if task_response.status == "success":
                st.success("流程执行完成。")
            else:
                st.error(task_response.message)

task_response = get_task_response()
result = get_workflow_result()
if result is not None:
    render_result_overview(
        build_workflow_overview(
            result,
            title="诊断结果总览",
            next_step="先看映射、STG 和质量规则建议，再去评审页面处理人工确认。",
        )
    )
    if task_response is not None and task_response.exported_files:
        st.info("本次运行已导出报告，可以在报告页查看。")

    with st.expander("技能输出汇总", expanded=False):
        render_deferred_dataframe_section(
            "技能输出汇总",
            lambda: skill_outputs_to_dataframe(result.skill_outputs),
            empty_message="暂无可展示的技能输出。",
            compact=True,
            key_prefix="diagnosis_skill_summaries",
        )

    with st.expander("问题清单", expanded=False):
        render_deferred_dataframe_section(
            "问题清单",
            lambda: issues_to_dataframe(result.issues),
            empty_message="暂无诊断问题。",
            compact=True,
            key_prefix="diagnosis_issues",
        )

    with st.expander("治理任务", expanded=False):
        render_deferred_dataframe_section(
            "治理任务",
            lambda: tasks_to_dataframe(result.tasks),
            empty_message="暂无治理任务。",
            compact=True,
            key_prefix="diagnosis_tasks",
        )

    if result.mapping_results or result.unmapped_fields or result.mapping_summary:
        render_explanation_block(
            "标准映射概览",
            summary=result.mapping_summary or "暂无映射汇总。",
            next_step="请先评审映射建议，再确认或导出下游资产。",
        )

        with st.expander("映射结果", expanded=False):
            render_deferred_dataframe_section(
                "映射结果",
                lambda: mapping_results_to_dataframe(result.mapping_results),
                empty_message="暂无标准映射推荐。",
                compact=True,
                key_prefix="diagnosis_mapping_results",
            )

        with st.expander("未映射或低置信字段", expanded=False):
            render_deferred_dataframe_section(
                "未映射或低置信字段",
                lambda: unmapped_fields_to_dataframe(result.unmapped_fields),
                empty_message="暂无未映射或低置信字段。",
                compact=True,
                key_prefix="diagnosis_unmapped_fields",
            )

    if result.confirmed_mapping_results:
        with st.expander("已确认映射结果", expanded=False):
            render_deferred_dataframe_section(
                "已确认映射结果",
                lambda: mapping_results_to_dataframe(result.confirmed_mapping_results),
                empty_message="暂无已确认映射结果。",
                compact=True,
                key_prefix="diagnosis_confirmed_mapping",
            )

    if result.stg_suggestions or result.stg_field_suggestions or result.stg_summary:
        render_explanation_block(
            "STG 概览",
            summary=result.stg_summary or "暂无 STG 汇总。",
            next_step="请先评审 STG 字段建议，再确认最终结构。",
        )

        with st.expander("STG 表建议", expanded=False):
            render_deferred_dataframe_section(
                "STG 表建议",
                lambda: stg_tables_to_dataframe(result.stg_suggestions),
                empty_message="暂无 STG 表建议。",
                compact=True,
                key_prefix="diagnosis_stg_tables",
            )

        with st.expander("STG 字段建议", expanded=False):
            render_deferred_dataframe_section(
                "STG 字段建议",
                lambda: stg_fields_to_dataframe(result.stg_field_suggestions),
                empty_message="暂无 STG 字段建议。",
                columns=[
                    "source_table_name",
                    "source_field_name",
                    "recommended_stg_field_name",
                    "recommended_stg_field_name_cn",
                    "recommended_data_type",
                    "mapping_source",
                    "action",
                    "notes",
                ],
                compact=True,
                key_prefix="diagnosis_stg_fields",
            )

    if result.confirmed_stg_suggestions:
        with st.expander("已确认 STG 建议", expanded=False):
            render_deferred_dataframe_section(
                "已确认 STG 建议",
                lambda: stg_fields_to_dataframe(result.confirmed_stg_suggestions),
                empty_message="暂无已确认 STG 建议。",
                compact=True,
                key_prefix="diagnosis_confirmed_stg",
            )

    if result.quality_rule_suggestions or result.quality_rule_summary:
        render_explanation_block(
            "质量规则概览",
            summary=result.quality_rule_summary or "暂无质量规则汇总。",
            next_step="进入质量规则页确认、编辑或导出建议规则。",
        )

        with st.expander("质量规则建议", expanded=False):
            render_deferred_dataframe_section(
                "质量规则建议",
                lambda: quality_rules_to_dataframe(result.quality_rule_suggestions),
                empty_message="暂无质量规则推荐。",
                compact=True,
                key_prefix="diagnosis_quality_rules",
            )

    if result.review_summary is not None:
        with st.expander("评审汇总", expanded=False):
            render_deferred_dataframe_section(
                "评审汇总",
                lambda: review_summary_to_dataframe(result.review_summary),
                empty_message="暂无评审汇总。",
                compact=True,
                key_prefix="diagnosis_review_summary",
            )

    if result.mapping_results or result.stg_field_suggestions or result.quality_rule_suggestions:
        st.info("下一步：进入评审页，对建议进行接受、拒绝、编辑或标记人工复核。")
