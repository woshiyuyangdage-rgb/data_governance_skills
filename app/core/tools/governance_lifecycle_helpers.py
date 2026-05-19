"""Payload and resolution helpers for governance lifecycle tool handlers."""

import json
from pathlib import Path
from typing import Protocol

import app.core.governance.backlog_store as backlog_store
from app.core.governance import (
    BacklogSlaCalculator,
    GapClassifier,
    GovernanceBacklogTrackingService,
    ReadinessAssessor,
    RemediationPlanner,
)
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.remediation_action import RemediationAction
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_backlog_package_from_file,
    run_full_governance_portfolio_package_from_file,
    run_full_governance_work_package_from_file,
    run_governance_backlog_build_from_file,
    run_governance_portfolio_assessment_from_file,
    run_governance_readiness_assessment_from_file,
    run_governance_readiness_assessment_with_review_from_file,
)
from app.core.utils.time_utils import utc_now_compact


class GovernanceLifecycleToolContext(Protocol):
    """Subset of executor helpers used by lifecycle resolution functions."""

    def _optional_string(
        self, arguments: dict[str, object], name: str
    ) -> str | None: ...

    def _optional_workflow_result(
        self, arguments: dict[str, object]
    ) -> WorkflowResult | None: ...


def coerce_governance_backlog_items(
    payload: object,
) -> list[GovernanceBacklogItem]:
    """Coerce a raw payload into backlog items."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("governance_backlog_items must be a list.")
    return [
        item
        if isinstance(item, GovernanceBacklogItem)
        else GovernanceBacklogItem.model_validate(item)
        for item in payload
    ]


def coerce_backlog_sla_statuses(payload: object) -> list[BacklogSlaStatus]:
    """Coerce a raw payload into backlog SLA status records."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("backlog_sla_statuses must be a list.")
    return [
        item
        if isinstance(item, BacklogSlaStatus)
        else BacklogSlaStatus.model_validate(item)
        for item in payload
    ]


def coerce_remediation_actions(payload: object) -> list[RemediationAction]:
    """Coerce a raw payload into remediation actions."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("remediation_actions must be a list.")
    return [
        item
        if isinstance(item, RemediationAction)
        else RemediationAction.model_validate(item)
        for item in payload
    ]


def resolve_readiness_result_from_arguments(
    context: GovernanceLifecycleToolContext,
    arguments: dict[str, object],
    *,
    full_work_package: bool,
) -> WorkflowResult:
    """Resolve or compute readiness outputs from a workflow result or file path."""
    workflow_result = context._optional_workflow_result(arguments)
    file_path = context._optional_string(arguments, "file_path")
    if file_path:
        if full_work_package:
            return run_full_governance_work_package_from_file(file_path)
        if bool(arguments.get("apply_review_replay", False)):
            return run_governance_readiness_assessment_with_review_from_file(file_path)
        return run_governance_readiness_assessment_from_file(file_path)

    if workflow_result is None:
        raise ValueError("workflow_result or file_path is required.")

    assessor = ReadinessAssessor()
    classifier = GapClassifier()
    planner = RemediationPlanner()

    if not workflow_result.readiness_scores:
        workflow_result.readiness_scores = assessor.assess(workflow_result)
    if not workflow_result.governance_gaps:
        workflow_result.governance_gaps = classifier.classify(workflow_result)
    if full_work_package or not workflow_result.remediation_actions:
        workflow_result.remediation_actions = planner.build_actions(
            workflow_result.readiness_scores,
            workflow_result.governance_gaps,
        )
    if full_work_package and workflow_result.governance_work_package is None:
        package_name = (
            context._optional_string(arguments, "package_name")
            or "governance_work_package"
        )
        workflow_result.governance_work_package = planner.build_work_package(
            workflow_result.readiness_scores,
            workflow_result.governance_gaps,
            workflow_result.remediation_actions,
            package_name=package_name,
        )
    if not workflow_result.readiness_summary:
        workflow_result.readiness_summary = planner.summarize(
            workflow_result.readiness_scores,
            workflow_result.governance_gaps,
            workflow_result.remediation_actions,
        )
    return workflow_result


def maybe_export_governance_work_package(
    context: GovernanceLifecycleToolContext,
    arguments: dict[str, object],
    workflow_result: WorkflowResult,
) -> dict[str, str]:
    """Write the governance work package as a local JSON asset when requested."""
    work_package = workflow_result.governance_work_package
    if work_package is None:
        return {}
    should_export = bool(arguments.get("export_package", False)) or bool(
        context._optional_string(arguments, "output_dir")
    )
    if not should_export:
        return {}

    output_dir = Path(
        context._optional_string(arguments, "output_dir")
        or (
            Path(__file__).resolve().parents[3]
            / "outputs"
            / "governance_work_packages"
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    base_filename = (
        context._optional_string(arguments, "base_filename")
        or f"governance_work_package_{utc_now_compact()}"
    )
    output_path = output_dir / f"{base_filename}.json"
    output_path.write_text(
        json.dumps(work_package.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"governance_work_package": str(output_path)}


def resolve_backlog_items_from_arguments(
    context: GovernanceLifecycleToolContext,
    arguments: dict[str, object],
) -> tuple[list[GovernanceBacklogItem], WorkflowResult | None]:
    """Resolve or build backlog items from tool arguments."""
    provided_items = coerce_governance_backlog_items(
        arguments.get("governance_backlog_items")
    )
    if provided_items:
        return provided_items, context._optional_workflow_result(arguments)

    workflow_result = context._optional_workflow_result(arguments)
    file_path = context._optional_string(arguments, "file_path")
    if file_path:
        apply_review_replay = bool(arguments.get("apply_review_replay", True))
        workflow_result = (
            run_full_governance_backlog_package_from_file(file_path)
            if apply_review_replay
            else run_governance_backlog_build_from_file(file_path)
        )
        return list(workflow_result.governance_backlog_items), workflow_result

    service = GovernanceBacklogTrackingService()
    if workflow_result is None:
        remediation_actions = coerce_remediation_actions(
            arguments.get("remediation_actions")
        )
        if not remediation_actions:
            return [], None
        items, _ = service.builder.build_backlog(remediation_actions)
        return items, None

    if not workflow_result.remediation_actions:
        workflow_result = resolve_readiness_result_from_arguments(
            context,
            {"workflow_result": workflow_result},
            full_work_package=True,
        )
    items, summary = service.build_backlog_from_work_package(
        workflow_result=workflow_result
    )
    workflow_result.governance_backlog_items = items
    workflow_result.backlog_summary = summary
    return items, workflow_result


def resolve_portfolio_inputs(
    context: GovernanceLifecycleToolContext,
    arguments: dict[str, object],
) -> tuple[list[GovernanceBacklogItem], list[BacklogSlaStatus], WorkflowResult | None]:
    """Resolve backlog and SLA inputs for portfolio-level tools."""
    workflow_result = context._optional_workflow_result(arguments)
    file_path = context._optional_string(arguments, "file_path")
    if file_path:
        workflow_result = (
            run_full_governance_portfolio_package_from_file(file_path)
            if bool(arguments.get("apply_review_replay", True))
            else run_governance_portfolio_assessment_from_file(file_path)
        )
        return (
            list(workflow_result.governance_backlog_items),
            list(workflow_result.backlog_sla_statuses),
            workflow_result,
        )

    items = coerce_governance_backlog_items(arguments.get("governance_backlog_items"))
    if workflow_result is not None and not items:
        if not workflow_result.governance_backlog_items:
            if not workflow_result.remediation_actions:
                workflow_result = resolve_readiness_result_from_arguments(
                    context,
                    {"workflow_result": workflow_result},
                    full_work_package=True,
                )
            items, summary = (
                GovernanceBacklogTrackingService().build_backlog_from_work_package(
                    workflow_result=workflow_result
                )
            )
            workflow_result.governance_backlog_items = items
            workflow_result.backlog_summary = summary
        else:
            items = list(workflow_result.governance_backlog_items)
    if not items:
        items = backlog_store.list_backlog_items()

    sla_statuses = coerce_backlog_sla_statuses(arguments.get("backlog_sla_statuses"))
    if not sla_statuses:
        sla_statuses = BacklogSlaCalculator().calculate(items)
    if workflow_result is not None:
        workflow_result.governance_backlog_items = items
        workflow_result.backlog_sla_statuses = sla_statuses
    return items, sla_statuses, workflow_result
