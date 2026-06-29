"""Helpers for building page-level result overviews."""

from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.config_status import ConfigStatus
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.result_overview import ResultOverview, ResultOverviewMetric
from app.core.models.validation_result import ValidationResult
from app.core.models.workflow_result import WorkflowResult
from app.ui.result_overview import (
    build_agent_shell_overview as _build_agent_shell_overview,
)
from app.ui.result_overview import (
    build_config_edit_overview as _build_config_edit_overview,
)
from app.ui.result_overview import (
    build_intent_execution_overview as _build_intent_execution_overview,
)
from app.ui.result_overview import (
    build_validation_overview as _build_validation_overview,
)
from app.ui.result_overview import (
    build_workflow_result_overview as _build_workflow_result_overview,
)


def build_status_overview(status: ConfigStatus) -> ResultOverview:
    """Build a normalized overview for a control-plane asset status."""
    return ResultOverview(
        title="资产状态总览",
        status=status.current_status,
        details=[
            ("资产", status.asset_name),
            ("类型", status.asset_type or "N/A"),
            ("文件", status.file_path or "N/A"),
            ("最近校验", status.last_validated_at or "N/A"),
            ("最近发布", status.last_published_at or "N/A"),
        ],
        metrics=[
            ResultOverviewMetric(label="状态", value=status.current_status),
        ],
        warnings=[status.last_error_message] if status.last_error_message else [],
        next_step="先校验当前配置；校验通过后再发布，必要时可从备份回滚。",
    )


def build_validation_overview(
    result: ValidationResult,
    *,
    title: str = "校验结果总览",
) -> ResultOverview:
    """Build a normalized overview for validation output."""
    return _build_validation_overview(result, title=title)


def build_config_edit_overview(
    result: ConfigEditResult,
    *,
    title: str = "控制面结果",
) -> ResultOverview:
    """Build a normalized overview for control-plane edit output."""
    return _build_config_edit_overview(result, title=title)


def build_workflow_overview(
    result: WorkflowResult,
    *,
    title: str = "结果总览",
    summary: str | None = None,
    next_step: str | None = None,
) -> ResultOverview:
    """Build a normalized overview for workflow output."""
    return _build_workflow_result_overview(
        result,
        title=title,
        summary=summary,
        next_step=next_step,
    )


def build_intent_overview(
    result: IntentExecutionResult,
    *,
    title: str = "意图解析总览",
) -> ResultOverview:
    """Build a normalized overview for intent output."""
    return _build_intent_execution_overview(result, title=title)


def build_agent_overview(
    result: AgentShellResult,
    *,
    title: str = "Agent 总览",
) -> ResultOverview:
    """Build a normalized overview for agent shell output."""
    return _build_agent_shell_overview(result, title=title)
