"""Shared render helpers for normalized result overviews."""

from pathlib import Path
from typing import Mapping

import streamlit as st

from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.result_overview import (
    ResultOverview,
    ResultOverviewArtifact,
    ResultOverviewMetric,
)
from app.core.models.validation_result import ValidationResult
from app.core.models.workflow_result import WorkflowResult
from app.ui.status_blocks import render_key_value_block, render_metric_row
from app.ui.workbench_cache import file_cache_key, read_file_bytes_cached


def build_result_artifacts(
    exported_files: Mapping[str, str] | None,
    *,
    mime_by_label: Mapping[str, str] | None = None,
) -> list[ResultOverviewArtifact]:
    """Convert exported file paths into normalized result artifacts."""
    if not exported_files:
        return []

    return [
        ResultOverviewArtifact(
            label=label,
            path=path,
            mime=mime_by_label.get(label) if mime_by_label is not None else None,
        )
        for label, path in exported_files.items()
    ]


def artifact_download_key(label: str, path: Path) -> str:
    """Build a stable Streamlit download key for one result artifact."""
    return f"download_{label}_{path.as_posix()}"


def render_result_artifacts(
    artifacts: list[ResultOverviewArtifact],
    *,
    use_container_width: bool = False,
) -> None:
    """Render artifact links and download buttons for a result overview."""
    if not artifacts:
        return

    st.markdown("**附件**")
    for artifact in artifacts:
        if not artifact.path:
            st.write(f"- {artifact.label}: N/A")
            continue

        resolved_path = Path(artifact.path)
        st.write(f"- {artifact.label}: `{resolved_path}`")
        if resolved_path.exists():
            mime = artifact.mime or "application/octet-stream"
            path_text = str(resolved_path)
            st.download_button(
                label=f"下载 {artifact.label}",
                data=read_file_bytes_cached(path_text, file_cache_key(path_text)),
                file_name=resolved_path.name,
                mime=mime,
                key=artifact_download_key(artifact.label, resolved_path),
                use_container_width=use_container_width,
            )


def render_result_overview(overview: ResultOverview) -> None:
    """Render a consistent result overview block."""
    details = list(overview.details)
    if overview.status:
        details = [("状态", overview.status)] + details

    render_key_value_block(
        overview.title,
        summary=overview.summary,
        rows=details,
        empty_message="No details available.",
    )

    if overview.metrics:
        render_metric_row(
            [(metric.label, metric.value, metric.help_text) for metric in overview.metrics]
        )

    if overview.warnings:
        for warning in overview.warnings:
            st.warning(warning)

    if overview.next_step:
        st.info(overview.next_step)

    render_result_artifacts(overview.artifacts)


def build_workflow_result_overview(
    result: WorkflowResult,
    *,
    title: str = "结果总览",
    summary: str | None = None,
    next_step: str | None = None,
) -> ResultOverview:
    """Build a normalized overview for workflow-style results."""
    return ResultOverview(
        title=title,
        summary=summary or result.message or "工作流结果总览。",
        status=result.status,
        details=[
            ("输入表数", result.input_table_count),
            ("问题数", result.issue_count),
            ("任务数", result.task_count),
            ("映射建议", len(result.mapping_results)),
            ("STG 建议", len(result.stg_field_suggestions)),
            ("质量规则", len(result.quality_rule_suggestions)),
            ("确认映射", len(result.confirmed_mapping_results)),
            ("确认 STG", len(result.confirmed_stg_suggestions)),
            ("确认质量规则", len(result.confirmed_quality_rules)),
        ],
        metrics=[
            ResultOverviewMetric(label="问题", value=result.issue_count),
            ResultOverviewMetric(label="映射", value=len(result.mapping_results)),
            ResultOverviewMetric(label="STG", value=len(result.stg_field_suggestions)),
            ResultOverviewMetric(label="质量规则", value=len(result.quality_rule_suggestions)),
        ],
        next_step=next_step or "先看建议，再去评审页固化覆盖。",
    )


def build_intent_execution_overview(
    result: IntentExecutionResult,
    *,
    title: str = "意图解析总览",
) -> ResultOverview:
    """Build a normalized overview for intent execution results."""
    intent = result.interpreted_intent
    task_response = result.task_response
    details = [
        ("匹配意图", intent.matched_intent_name or "fallback"),
        ("匹配方案", intent.matched_profile_name or "N/A"),
        ("匹配来源", intent.match_source),
        ("关键词", ", ".join(intent.matched_keywords) or "N/A"),
        ("回退解析", intent.fallback_used),
        ("本地相似度", intent.nlp_similarity),
        ("文件路径", result.task_request.file_path or "N/A"),
    ]
    artifacts: list[ResultOverviewArtifact] = []
    if task_response is not None:
        details.extend(
            [
                ("执行方案", task_response.profile_name),
                ("执行阶段", ", ".join(task_response.stages_executed) or "N/A"),
                ("执行状态", task_response.status),
            ]
        )
        artifacts = build_result_artifacts(task_response.exported_files)

    return ResultOverview(
        title=title,
        summary=intent.message or (task_response.message if task_response else None),
        status=task_response.status if task_response is not None else "preview",
        details=details,
        metrics=[ResultOverviewMetric(label="置信度", value=intent.confidence)],
        artifacts=artifacts,
        next_step=(
            "如果结果可用，可以继续执行；如果不对，回到上传页补充上下文。"
            if task_response is None
            else "结果已生成，可以去报告页查看输出文件。"
        ),
    )


def build_agent_shell_overview(
    result: AgentShellResult,
    *,
    title: str = "Agent Shell 总览",
) -> ResultOverview:
    """Build a normalized overview for agent shell results."""
    plan = result.execution_plan
    context = result.resolved_context
    warnings = list(plan.validation_messages)
    if context is not None and context.ambiguity_detected:
        warnings.append("上下文解析存在歧义，建议先确认参数。")
    if result.status == "validation_failed":
        warnings.append(result.message)

    resolved_file_path = plan.file_path or (
        context.resolved_file_path if context is not None else "N/A"
    )

    details = [
        ("会话 ID", result.session_id or "N/A"),
        ("匹配方案", result.interpreted_intent.matched_profile_name or "N/A"),
        ("匹配来源", result.interpreted_intent.match_source),
        ("阶段", ", ".join(plan.stages) or "N/A"),
        ("需要确认", plan.requires_confirmation),
        ("校验通过", plan.validation_passed),
        ("输出模式", plan.suggested_output_mode or "N/A"),
        ("文件路径", resolved_file_path),
    ]
    if context is not None:
        details.extend(
            [
                ("解析来源", ", ".join(context.resolved_from) or "N/A"),
                ("自动补全", context.autofilled_parameters or "N/A"),
            ]
        )

    artifacts: list[ResultOverviewArtifact] = []
    if result.task_response is not None:
        artifacts = build_result_artifacts(result.task_response.exported_files)

    return ResultOverview(
        title=title,
        summary=result.message or plan.summary,
        status=result.status,
        details=details,
        metrics=[
            ResultOverviewMetric(label="置信度", value=result.interpreted_intent.confidence),
            ResultOverviewMetric(label="阶段数", value=len(plan.stages)),
            ResultOverviewMetric(label="校验项", value=len(plan.validation_messages)),
        ],
        warnings=warnings,
        artifacts=artifacts,
        next_step=(
            "先看校验和上下文解析，再决定是否执行。"
            if result.task_response is None
            else "任务已执行，可回到报告页或评审页继续处理。"
        ),
    )


def build_validation_overview(
    result: ValidationResult,
    *,
    title: str = "校验结果总览",
) -> ResultOverview:
    """Build a normalized overview for control-plane validation results."""
    return ResultOverview(
        title=title,
        summary="配置校验结果已生成。",
        status="valid" if result.is_valid else "invalid",
        details=[
            ("资产", result.asset_name),
            ("校验通过", result.is_valid),
            ("错误数", len(result.messages)),
            ("警告数", len(result.warnings)),
        ],
        warnings=list(result.messages) + list(result.warnings),
        metrics=[
            ResultOverviewMetric(label="错误", value=len(result.messages)),
            ResultOverviewMetric(label="警告", value=len(result.warnings)),
        ],
        next_step="如果没有错误，可以继续保存或发布；如果有错误，先修正再重试。",
    )


def build_config_edit_overview(
    result: ConfigEditResult,
    *,
    title: str = "控制面结果",
) -> ResultOverview:
    """Build a normalized overview for control-plane edit results."""
    validation = result.validation_result
    warnings = []
    if validation is not None:
        warnings.extend(validation.messages)
        warnings.extend(validation.warnings)

    return ResultOverview(
        title=title,
        summary=result.message,
        status=result.status,
        details=[
            ("资产", result.asset_name),
            ("备份", result.backup_path or "N/A"),
            ("校验通过", validation.is_valid if validation is not None else "N/A"),
        ],
        warnings=warnings,
        metrics=[
            ResultOverviewMetric(label="状态", value=result.status),
            ResultOverviewMetric(
                label="错误",
                value=len(validation.messages) if validation is not None else 0,
            ),
            ResultOverviewMetric(
                label="警告",
                value=len(validation.warnings) if validation is not None else 0,
            ),
        ],
        next_step="查看备份、校验信息和变更内容，再决定是否发布。",
    )
