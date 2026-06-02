"""Shared Streamlit viewer for workflow result detail tables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.core.models.workflow_result import WorkflowResult
from app.ui.performance_helpers import render_deferred_dataframe_section
from app.ui.workbench_cache import (
    ai_ready_scores_to_dataframe,
    backlog_sla_statuses_to_dataframe,
    backlog_summary_to_dataframe,
    confirmed_quality_rules_to_dataframe,
    execution_package_export_results_to_dataframe,
    execution_package_summary_to_dataframe,
    execution_ready_rules_to_dataframe,
    field_description_suggestions_to_dataframe,
    governance_backlog_items_to_dataframe,
    governance_gaps_to_dataframe,
    governance_portfolio_summary_to_dataframe,
    governance_work_package_summary_to_dataframe,
    issues_to_dataframe,
    mapping_results_to_dataframe,
    progress_snapshot_to_dataframe,
    quality_rule_packages_to_dataframe,
    quality_rules_to_dataframe,
    rag_quality_issues_to_dataframe,
    readiness_scores_to_dataframe,
    remediation_actions_to_dataframe,
    review_summary_to_dataframe,
    rule_export_results_to_dataframe,
    skill_outputs_to_dataframe,
    stg_fields_to_dataframe,
    stg_tables_to_dataframe,
    table_semantic_summaries_to_dataframe,
    tasks_to_dataframe,
    text_to_sql_readiness_issues_to_dataframe,
    text_to_sql_readiness_scores_to_dataframe,
    unmapped_fields_to_dataframe,
)


@dataclass(frozen=True)
class ResultDetailSection:
    """One lazily-rendered result detail table."""

    group: str
    title: str
    count: int
    dataframe_builder: Callable[[], pd.DataFrame]
    empty_message: str
    columns: list[str] | None = None


def _present(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return True


def _count(value: object | None) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return 1


def _section(
    result: WorkflowResult,
    *,
    group: str,
    title: str,
    attribute: str,
    dataframe_builder: Callable[[object], pd.DataFrame],
    empty_message: str,
    columns: list[str] | None = None,
) -> ResultDetailSection | None:
    value = getattr(result, attribute)
    if not _present(value):
        return None
    return ResultDetailSection(
        group=group,
        title=title,
        count=_count(value),
        dataframe_builder=lambda value=value: dataframe_builder(value),
        empty_message=empty_message,
        columns=columns,
    )


def build_result_detail_sections(result: WorkflowResult) -> list[ResultDetailSection]:
    """Build all non-empty detail sections for one workflow result."""
    section_specs = [
        {
            "group": "诊断与语义",
            "title": "技能输出",
            "attribute": "skill_outputs",
            "dataframe_builder": skill_outputs_to_dataframe,
            "empty_message": "暂无技能输出。",
        },
        {
            "group": "诊断与语义",
            "title": "问题清单",
            "attribute": "issues",
            "dataframe_builder": issues_to_dataframe,
            "empty_message": "暂无诊断问题。",
        },
        {
            "group": "诊断与语义",
            "title": "治理任务",
            "attribute": "tasks",
            "dataframe_builder": tasks_to_dataframe,
            "empty_message": "暂无治理任务。",
        },
        {
            "group": "诊断与语义",
            "title": "字段描述建议",
            "attribute": "field_description_suggestions",
            "dataframe_builder": field_description_suggestions_to_dataframe,
            "empty_message": "暂无字段描述建议。",
        },
        {
            "group": "诊断与语义",
            "title": "表级语义摘要",
            "attribute": "table_semantic_summaries",
            "dataframe_builder": table_semantic_summaries_to_dataframe,
            "empty_message": "暂无表级语义摘要。",
        },
        {
            "group": "标准映射与 STG",
            "title": "标准映射推荐",
            "attribute": "mapping_results",
            "dataframe_builder": mapping_results_to_dataframe,
            "empty_message": "暂无标准映射推荐。",
        },
        {
            "group": "标准映射与 STG",
            "title": "已确认映射",
            "attribute": "confirmed_mapping_results",
            "dataframe_builder": mapping_results_to_dataframe,
            "empty_message": "暂无已确认映射。",
        },
        {
            "group": "标准映射与 STG",
            "title": "未映射或低置信字段",
            "attribute": "unmapped_fields",
            "dataframe_builder": unmapped_fields_to_dataframe,
            "empty_message": "暂无未映射或低置信字段。",
        },
        {
            "group": "标准映射与 STG",
            "title": "STG 表建议",
            "attribute": "stg_suggestions",
            "dataframe_builder": stg_tables_to_dataframe,
            "empty_message": "暂无 STG 表建议。",
        },
        {
            "group": "标准映射与 STG",
            "title": "STG 字段建议",
            "attribute": "stg_field_suggestions",
            "dataframe_builder": stg_fields_to_dataframe,
            "empty_message": "暂无 STG 字段建议。",
            "columns": [
                "source_table_name",
                "source_field_name",
                "recommended_stg_field_name",
                "recommended_stg_field_name_cn",
                "recommended_data_type",
                "mapping_source",
                "action",
                "notes",
            ],
        },
        {
            "group": "标准映射与 STG",
            "title": "已确认 STG 建议",
            "attribute": "confirmed_stg_suggestions",
            "dataframe_builder": stg_fields_to_dataframe,
            "empty_message": "暂无已确认 STG 建议。",
        },
        {
            "group": "质量规则",
            "title": "质量规则建议",
            "attribute": "quality_rule_suggestions",
            "dataframe_builder": quality_rules_to_dataframe,
            "empty_message": "暂无质量规则建议。",
        },
        {
            "group": "质量规则",
            "title": "质量规则包",
            "attribute": "quality_rule_packages",
            "dataframe_builder": quality_rule_packages_to_dataframe,
            "empty_message": "暂无质量规则包。",
        },
        {
            "group": "质量规则",
            "title": "已确认质量规则",
            "attribute": "confirmed_quality_rules",
            "dataframe_builder": confirmed_quality_rules_to_dataframe,
            "empty_message": "暂无已确认质量规则。",
        },
        {
            "group": "质量规则",
            "title": "可执行规则",
            "attribute": "execution_ready_package",
            "dataframe_builder": execution_ready_rules_to_dataframe,
            "empty_message": "暂无可执行规则。",
        },
        {
            "group": "质量规则",
            "title": "规则导出结果",
            "attribute": "rule_export_results",
            "dataframe_builder": rule_export_results_to_dataframe,
            "empty_message": "暂无规则导出结果。",
        },
        {
            "group": "AI 准备度",
            "title": "治理准备度评分",
            "attribute": "readiness_scores",
            "dataframe_builder": readiness_scores_to_dataframe,
            "empty_message": "暂无治理准备度评分。",
        },
        {
            "group": "AI 准备度",
            "title": "AI-ready 评分",
            "attribute": "ai_ready_scores",
            "dataframe_builder": ai_ready_scores_to_dataframe,
            "empty_message": "暂无 AI-ready 评分。",
        },
        {
            "group": "AI 准备度",
            "title": "RAG 知识库问题",
            "attribute": "rag_quality_issues",
            "dataframe_builder": rag_quality_issues_to_dataframe,
            "empty_message": "暂无 RAG 知识库问题。",
        },
        {
            "group": "AI 准备度",
            "title": "Text-to-SQL 准备度评分",
            "attribute": "text_to_sql_readiness_scores",
            "dataframe_builder": text_to_sql_readiness_scores_to_dataframe,
            "empty_message": "暂无 Text-to-SQL 准备度评分。",
        },
        {
            "group": "AI 准备度",
            "title": "Text-to-SQL 问题",
            "attribute": "text_to_sql_readiness_issues",
            "dataframe_builder": text_to_sql_readiness_issues_to_dataframe,
            "empty_message": "暂无 Text-to-SQL 问题。",
        },
        {
            "group": "治理计划",
            "title": "治理缺口",
            "attribute": "governance_gaps",
            "dataframe_builder": governance_gaps_to_dataframe,
            "empty_message": "暂无治理缺口。",
        },
        {
            "group": "治理计划",
            "title": "整改动作",
            "attribute": "remediation_actions",
            "dataframe_builder": remediation_actions_to_dataframe,
            "empty_message": "暂无整改动作。",
        },
        {
            "group": "治理计划",
            "title": "治理工作包",
            "attribute": "governance_work_package",
            "dataframe_builder": governance_work_package_summary_to_dataframe,
            "empty_message": "暂无治理工作包。",
        },
        {
            "group": "治理计划",
            "title": "待办清单",
            "attribute": "governance_backlog_items",
            "dataframe_builder": governance_backlog_items_to_dataframe,
            "empty_message": "暂无待办清单。",
        },
        {
            "group": "治理计划",
            "title": "待办汇总",
            "attribute": "backlog_summary",
            "dataframe_builder": backlog_summary_to_dataframe,
            "empty_message": "暂无待办汇总。",
        },
        {
            "group": "治理计划",
            "title": "SLA 状态",
            "attribute": "backlog_sla_statuses",
            "dataframe_builder": backlog_sla_statuses_to_dataframe,
            "empty_message": "暂无 SLA 状态。",
        },
        {
            "group": "治理计划",
            "title": "组合治理汇总",
            "attribute": "governance_portfolio_summary",
            "dataframe_builder": governance_portfolio_summary_to_dataframe,
            "empty_message": "暂无组合治理汇总。",
        },
        {
            "group": "治理计划",
            "title": "进度快照",
            "attribute": "progress_snapshot",
            "dataframe_builder": progress_snapshot_to_dataframe,
            "empty_message": "暂无进度快照。",
        },
        {
            "group": "交付与复核",
            "title": "复核汇总",
            "attribute": "review_summary",
            "dataframe_builder": review_summary_to_dataframe,
            "empty_message": "暂无复核汇总。",
        },
        {
            "group": "交付与复核",
            "title": "执行包汇总",
            "attribute": "execution_ready_package",
            "dataframe_builder": execution_package_summary_to_dataframe,
            "empty_message": "暂无执行包汇总。",
        },
        {
            "group": "交付与复核",
            "title": "执行包导出结果",
            "attribute": "execution_package_export_results",
            "dataframe_builder": execution_package_export_results_to_dataframe,
            "empty_message": "暂无执行包导出结果。",
        },
    ]

    sections: list[ResultDetailSection] = []
    for spec in section_specs:
        section = _section(result, **spec)
        if section is not None:
            sections.append(section)
    return sections


def render_result_detail_viewer(
    result: WorkflowResult,
    *,
    key_prefix: str = "result_detail_viewer",
) -> None:
    """Render grouped on-page detail tables for one workflow result."""
    sections = build_result_detail_sections(result)
    if not sections:
        st.info("当前结果暂无可在页面查看的明细。")
        return

    groups = list(dict.fromkeys(section.group for section in sections))
    tab_by_group = dict(zip(groups, st.tabs(groups)))
    for group in groups:
        group_sections = [section for section in sections if section.group == group]
        total_count = sum(section.count for section in group_sections)
        with tab_by_group[group]:
            st.caption(f"本组包含 {len(group_sections)} 类明细，共 {total_count} 条记录。")
            for index, section in enumerate(group_sections):
                label = f"{section.title} ({section.count})"
                with st.expander(label, expanded=index == 0):
                    render_deferred_dataframe_section(
                        section.title,
                        section.dataframe_builder,
                        empty_message=section.empty_message,
                        columns=section.columns,
                        compact=True,
                        key_prefix=f"{key_prefix}_{group}_{index}_{section.title}",
                    )
