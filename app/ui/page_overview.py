"""Helpers for building page-level result overviews."""

from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.config_status import ConfigStatus
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.result_overview import ResultOverview, ResultOverviewMetric
from app.core.models.validation_result import ValidationResult
from app.core.models.workflow_result import WorkflowResult


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
        next_step="查看变更预览，再决定是否保存、发布或回滚。",
    )


def build_validation_overview(result: ValidationResult) -> ResultOverview:
    """Build a normalized overview for validation output."""
    from app.ui.result_overview import build_validation_overview as _build

    return _build(result)


def build_config_edit_overview(result: ConfigEditResult) -> ResultOverview:
    """Build a normalized overview for control-plane edit output."""
    from app.ui.result_overview import build_config_edit_overview as _build

    return _build(result)


def build_workflow_overview(result: WorkflowResult) -> ResultOverview:
    """Build a normalized overview for workflow output."""
    from app.ui.result_overview import build_workflow_result_overview as _build

    return _build(result)


def build_intent_overview(result: IntentExecutionResult) -> ResultOverview:
    """Build a normalized overview for intent output."""
    from app.ui.result_overview import build_intent_execution_overview as _build

    return _build(result)


def build_agent_overview(result: AgentShellResult) -> ResultOverview:
    """Build a normalized overview for agent shell output."""
    from app.ui.result_overview import build_agent_shell_overview as _build

    return _build(result)
