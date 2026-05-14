"""Standard local executor for governance tool contracts."""

import json
from pathlib import Path

import app.core.governance.backlog_store as backlog_store
from app.core.agent.agent_shell_service import AgentShellService
from app.core.agent.session_store import append_trace_to_session
from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.audit.trace_store import build_trace_summary, save_trace
from app.core.control_plane.control_plane_service import ControlPlaneService
from app.core.delivery.delivery_service import DeliveryService
from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.delivery.delivery_template_loader import (
    list_enabled_delivery_bundle_variants,
    list_enabled_delivery_template_profiles,
)
from app.core.delivery.confirmation_template_loader import (
    list_enabled_confirmation_template_profiles,
)
from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.governance import (
    BacklogSlaCalculator,
    GapClassifier,
    GovernanceBacklogTrackingService,
    GovernancePortfolioAggregator,
    ProgressSnapshotService,
    ReadinessAssessor,
    RemediationPlanner,
)
from app.core.governance.batch_snapshot_store import (
    list_batch_snapshots,
    load_latest_batch_snapshot,
)
from app.core.governance.incremental_diff_service import IncrementalDiffService
from app.core.intent.intent_task_service import interpret_and_run_task
from app.core.intake.intake_adapter_service import IntakeAdapterService
from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.execution_trace import ExecutionTrace
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.remediation_action import RemediationAction
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.task_service import run_governance_task
from app.core.orchestrator.pipeline_service import (
    run_batch_governance_delivery_from_files,
    run_batch_governance_workflow_from_files,
    run_full_governance_backlog_package_from_file,
    run_full_governance_portfolio_package_from_file,
    run_full_governance_work_package_from_file,
    run_governance_backlog_build_from_file,
    run_governance_backlog_build_with_review_from_file,
    run_governance_portfolio_assessment_from_file,
    run_governance_readiness_assessment_from_file,
    run_governance_readiness_assessment_with_review_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
)
from app.core.reports.report_service import (
    DEFAULT_REPORT_OUTPUT_DIR,
    build_report_base_filename,
    export_all_reports,
)
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.templates.project_template_service import ProjectTemplateService
from app.core.review.quality_override_store import (
    load_quality_rule_overrides,
    save_quality_rule_review_records,
)
from app.core.review.quality_batch_review_service import (
    bulk_accept_by_rule_type,
    bulk_accept_by_table,
    bulk_mark_manual_review_by_low_confidence,
    summarize_review_queue,
)
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.tools.agent_tools import AgentToolMixin
from app.core.tools.control_plane_tools import ControlPlaneToolMixin
from app.core.tools.dispatch_tools import ToolDispatchMixin
from app.core.utils.time_utils import utc_now_seconds


class GovernanceToolExecutor(ToolDispatchMixin, AgentToolMixin, ControlPlaneToolMixin):
    """Execute standardized governance tools with local audit traces."""

    def __init__(self) -> None:
        self.agent_shell_service = AgentShellService()
        self.control_plane_service = ControlPlaneService()

    @staticmethod
    def _utc_now() -> str:
        return utc_now_seconds()

    @staticmethod
    def _optional_string(arguments: dict[str, object], key: str) -> str | None:
        value = arguments.get(key)
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _require_text(arguments: dict[str, object]) -> str:
        text = str(arguments.get("text", "")).strip()
        if not text:
            raise ValueError("Argument 'text' is required.")
        return text

    @staticmethod
    def _summarize_arguments(arguments: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {}
        for key, value in arguments.items():
            if key in {"result", "workflow_result", "task_response"}:
                if isinstance(value, dict):
                    summary[key] = {
                        "provided": True,
                        "keys": sorted(value.keys())[:15],
                    }
                else:
                    summary[key] = {"provided": value is not None}
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                summary[key] = value
            elif isinstance(value, list):
                summary[key] = {"type": "list", "size": len(value)}
            elif isinstance(value, dict):
                summary[key] = {"type": "dict", "keys": sorted(value.keys())[:15]}
            else:
                summary[key] = str(value)
        return summary

    @staticmethod
    def _summarize_resolved_context(shell_result: AgentShellResult) -> dict[str, object]:
        resolved_context = shell_result.resolved_context
        if resolved_context is None:
            return {}
        return {
            "resolved_file_path": resolved_context.resolved_file_path,
            "resolved_output_dir": resolved_context.resolved_output_dir,
            "resolved_from": list(resolved_context.resolved_from),
            "reference_matches": list(resolved_context.reference_matches),
            "autofilled_parameters": dict(resolved_context.autofilled_parameters),
            "ambiguity_detected": resolved_context.ambiguity_detected,
            "messages": list(resolved_context.messages),
        }

    @staticmethod
    def _extract_profile_name(result: object, fallback: str | None = None) -> str | None:
        if isinstance(result, GovernanceTaskResponse):
            return result.profile_name
        if isinstance(result, IntentExecutionResult):
            return result.task_request.profile_name
        if isinstance(result, AgentShellResult):
            return result.task_request.profile_name
        return fallback

    @staticmethod
    def _extract_stages(result: object) -> list[str]:
        if isinstance(result, GovernanceTaskResponse):
            return list(result.stages_executed)
        if isinstance(result, AgentShellResult):
            return list(result.execution_plan.stages)
        return []

    @staticmethod
    def _extract_exported_files(result: object) -> dict[str, str]:
        if isinstance(result, GovernanceTaskResponse):
            return dict(result.exported_files or {})
        if isinstance(result, AgentShellResult) and result.task_response is not None:
            return dict(result.task_response.exported_files or {})
        return {}

    @staticmethod
    def _extract_review_summary(result: object) -> dict[str, object]:
        workflow_result: WorkflowResult | None = None
        if isinstance(result, GovernanceTaskResponse) and isinstance(
            result.result, WorkflowResult
        ):
            workflow_result = result.result
        elif (
            isinstance(result, AgentShellResult)
            and result.task_response is not None
            and isinstance(result.task_response.result, WorkflowResult)
        ):
            workflow_result = result.task_response.result

        if workflow_result is None or workflow_result.review_summary is None:
            return {}
        return workflow_result.review_summary.model_dump()

    @staticmethod
    def _collect_notes_from_agent_result(result: AgentShellResult) -> list[str]:
        notes: list[str] = []
        if result.resolution_applied:
            notes.append("Context resolution autofilled one or more parameters.")
        if result.resolved_context is not None and result.resolved_context.ambiguity_detected:
            notes.append("Context resolution detected ambiguity and required confirmation.")
        if result.execution_plan.requires_confirmation:
            notes.append("This plan required explicit confirmation before execution.")
        return notes

    @staticmethod
    def _coerce_workflow_result(arguments: dict[str, object]) -> WorkflowResult:
        payload = arguments.get("workflow_result", arguments.get("result"))
        if isinstance(payload, WorkflowResult):
            return payload
        if isinstance(payload, dict):
            if "result" in payload and isinstance(payload.get("result"), dict):
                return WorkflowResult.model_validate(payload["result"])
            return WorkflowResult.model_validate(payload)
        raise ValueError(
            "Argument 'result' or 'workflow_result' must contain a workflow result payload."
        )

    @staticmethod
    def _optional_workflow_result(arguments: dict[str, object]) -> WorkflowResult | None:
        payload = arguments.get("workflow_result", arguments.get("result"))
        if payload is None:
            task_response_payload = arguments.get("task_response")
            if isinstance(task_response_payload, GovernanceTaskResponse):
                return task_response_payload.result
            if isinstance(task_response_payload, dict) and isinstance(
                task_response_payload.get("result"),
                dict,
            ):
                return WorkflowResult.model_validate(task_response_payload["result"])
            return None
        if isinstance(payload, WorkflowResult):
            return payload
        if isinstance(payload, dict):
            if "result" in payload and isinstance(payload.get("result"), dict):
                return WorkflowResult.model_validate(payload["result"])
            return WorkflowResult.model_validate(payload)
        return None

    @staticmethod
    def _coerce_quality_rule_suggestions(
        payload: object,
    ) -> list[QualityRuleSuggestion]:
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise ValueError("quality_rule_suggestions must be a list.")
        return [
            item
            if isinstance(item, QualityRuleSuggestion)
            else QualityRuleSuggestion.model_validate(item)
            for item in payload
        ]

    @staticmethod
    def _coerce_cross_field_quality_rules(
        payload: object,
    ) -> list[CrossFieldQualityRule]:
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise ValueError("cross_field_quality_rules must be a list.")
        return [
            item
            if isinstance(item, CrossFieldQualityRule)
            else CrossFieldQualityRule.model_validate(item)
            for item in payload
        ]

    @staticmethod
    def _cross_field_rules_as_suggestions(
        rules: list[CrossFieldQualityRule],
    ) -> list[QualityRuleSuggestion]:
        from app.core.skills.quality_rule_recommendation import (
            QualityRuleRecommendationSkill,
        )

        return [
            QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
            for rule in rules
        ]

    @staticmethod
    def _coerce_quality_review_records(payload: object) -> list[QualityRuleReviewRecord]:
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise ValueError("records must be a list.")
        return [
            item
            if isinstance(item, QualityRuleReviewRecord)
            else QualityRuleReviewRecord.model_validate(item)
            for item in payload
        ]

    @staticmethod
    def _coerce_confirmed_quality_rules(
        payload: object,
    ) -> list[ConfirmedQualityRule]:
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise ValueError("confirmed_quality_rules must be a list.")
        return [
            item
            if isinstance(item, ConfirmedQualityRule)
            else ConfirmedQualityRule.model_validate(item)
            for item in payload
        ]

    @staticmethod
    def _coerce_execution_ready_package(payload: object) -> ExecutionReadyPackage | None:
        if payload is None:
            return None
        if isinstance(payload, ExecutionReadyPackage):
            return payload
        if isinstance(payload, dict):
            return ExecutionReadyPackage.model_validate(payload)
        raise ValueError("execution_ready_package must be an object.")

    @staticmethod
    def _coerce_governance_backlog_items(
        payload: object,
    ) -> list[GovernanceBacklogItem]:
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

    @staticmethod
    def _coerce_backlog_sla_statuses(
        payload: object,
    ) -> list[BacklogSlaStatus]:
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

    @staticmethod
    def _coerce_remediation_actions(payload: object) -> list[RemediationAction]:
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

    @staticmethod
    def _resolve_export_profile_name(
        arguments: dict[str, object],
        workflow_result: WorkflowResult,
    ) -> str:
        profile_name = str(arguments.get("profile_name", "")).strip()
        if profile_name:
            return profile_name

        task_response_payload = arguments.get("task_response")
        if isinstance(task_response_payload, GovernanceTaskResponse):
            return task_response_payload.profile_name
        if isinstance(task_response_payload, dict):
            nested_profile = str(task_response_payload.get("profile_name", "")).strip()
            if nested_profile:
                return nested_profile

        preferred_mode = str(arguments.get("preferred_result_mode", "")).strip().lower()
        if preferred_mode == "confirmed":
            if workflow_result.quality_rule_suggestions:
                return "diagnosis_mapping_stg_quality_with_review"
            return "diagnosis_mapping_stg_with_review"
        if preferred_mode == "quality":
            return "diagnosis_mapping_stg_quality"
        if preferred_mode == "readiness":
            return "governance_readiness_assessment"
        if preferred_mode == "remediation":
            return "full_governance_work_package"
        if preferred_mode == "backlog":
            return "full_governance_backlog_package"
        if preferred_mode == "portfolio":
            return "full_governance_portfolio_package"
        if workflow_result.progress_snapshot is not None or workflow_result.governance_portfolio_summary is not None:
            return "full_governance_portfolio_package"
        if workflow_result.governance_backlog_items:
            return "full_governance_backlog_package"
        if workflow_result.governance_work_package is not None:
            return "full_governance_work_package"
        if workflow_result.readiness_scores or workflow_result.governance_gaps:
            return "governance_readiness_assessment"
        if workflow_result.confirmed_quality_rules:
            return "diagnosis_mapping_stg_quality_with_review"
        if workflow_result.quality_rule_suggestions:
            if workflow_result.review_summary is not None:
                return "diagnosis_mapping_stg_quality_with_review"
            return "diagnosis_mapping_stg_quality"
        if workflow_result.stg_suggestions or workflow_result.stg_field_suggestions:
            return "diagnosis_mapping_stg"
        if workflow_result.mapping_results:
            return "diagnosis_plus_mapping"
        return "metadata_diagnosis_only"

    def _start_trace(
        self,
        tool_name: str,
        arguments: dict[str, object],
        session_id: str | None = None,
        raw_text: str | None = None,
        profile_name: str | None = None,
        asset_name: str | None = None,
        operation: str | None = None,
    ) -> ExecutionTrace:
        trace = build_trace_summary(
            tool_name=tool_name,
            session_id=session_id,
            profile_name=profile_name,
            asset_name=asset_name,
            operation=operation,
            raw_text=raw_text,
            input_summary=self._summarize_arguments(arguments),
        )
        return trace

    def _finish_trace(
        self,
        trace: ExecutionTrace,
        status: str,
        message: str,
        stages_executed: list[str] | None = None,
        resolved_context_summary: dict[str, object] | None = None,
        exported_files: dict[str, str] | None = None,
        review_summary: dict[str, object] | None = None,
        notes: list[str] | None = None,
        asset_name: str | None = None,
        operation: str | None = None,
        validation_status: str | None = None,
        export_format: str | None = None,
        exported_rule_count: int | None = None,
        confirmed_rule_count: int | None = None,
        package_id: str | None = None,
        package_rule_count: int | None = None,
        exported_package_path: str | None = None,
        field_rule_count: int | None = None,
        cross_field_rule_count: int | None = None,
        low_confidence_rule_count: int | None = None,
        review_queue_summary: dict[str, object] | None = None,
        readiness_score_count: int | None = None,
        gap_count: int | None = None,
        remediation_action_count: int | None = None,
        work_package_name: str | None = None,
        backlog_item_count: int | None = None,
        backlog_status_summary: dict[str, object] | None = None,
        updated_backlog_id: str | None = None,
        old_status: str | None = None,
        new_status: str | None = None,
        overdue_count: int | None = None,
        blocked_count: int | None = None,
        owner_workload_summary: dict[str, object] | None = None,
        snapshot_id: str | None = None,
        workbook_count: int | None = None,
        delivery_package_name: str | None = None,
        delivery_output_dir: str | None = None,
        generated_file_count: int | None = None,
        batch_name: str | None = None,
        file_count: int | None = None,
        group_count: int | None = None,
        changed_count: int | None = None,
        new_count: int | None = None,
        unchanged_count: int | None = None,
        removed_count: int | None = None,
        rerun_object_count: int | None = None,
        workbook_type: str | None = None,
        imported_count: int | None = None,
        invalid_count: int | None = None,
        changed_object_count: int | None = None,
        rerun_changed_only: bool | None = None,
        domain_pack_name: str | None = None,
        template_name: str | None = None,
        domain_pack_match_confidence: float | None = None,
        applied_delivery_outputs: list[str] | None = None,
        intake_profile_name: str | None = None,
        intake_match_confidence: float | None = None,
        matched_sheet_name: str | None = None,
        unmapped_source_column_count: int | None = None,
        normalization_row_count: int | None = None,
        confirmation_template_name: str | None = None,
        template_match_confidence: float | None = None,
    ) -> ExecutionTrace:
        trace.status = status
        trace.message = message
        trace.finished_at = self._utc_now()
        trace.stages_executed = list(stages_executed or [])
        trace.resolved_context_summary = dict(resolved_context_summary or {})
        trace.exported_files = dict(exported_files or {})
        trace.review_summary = dict(review_summary or {})
        trace.notes = list(notes or [])
        if asset_name is not None:
            trace.asset_name = asset_name
        if operation is not None:
            trace.operation = operation
        if validation_status is not None:
            trace.validation_status = validation_status
        if export_format is not None:
            trace.export_format = export_format
        if exported_rule_count is not None:
            trace.exported_rule_count = exported_rule_count
        if confirmed_rule_count is not None:
            trace.confirmed_rule_count = confirmed_rule_count
        if package_id is not None:
            trace.package_id = package_id
        if package_rule_count is not None:
            trace.package_rule_count = package_rule_count
        if exported_package_path is not None:
            trace.exported_package_path = exported_package_path
        if field_rule_count is not None:
            trace.field_rule_count = field_rule_count
        if cross_field_rule_count is not None:
            trace.cross_field_rule_count = cross_field_rule_count
        if low_confidence_rule_count is not None:
            trace.low_confidence_rule_count = low_confidence_rule_count
        if review_queue_summary is not None:
            trace.review_queue_summary = dict(review_queue_summary)
        if readiness_score_count is not None:
            trace.readiness_score_count = readiness_score_count
        if gap_count is not None:
            trace.gap_count = gap_count
        if remediation_action_count is not None:
            trace.remediation_action_count = remediation_action_count
        if work_package_name is not None:
            trace.work_package_name = work_package_name
        if backlog_item_count is not None:
            trace.backlog_item_count = backlog_item_count
        if backlog_status_summary is not None:
            trace.backlog_status_summary = dict(backlog_status_summary)
        if updated_backlog_id is not None:
            trace.updated_backlog_id = updated_backlog_id
        if old_status is not None:
            trace.old_status = old_status
        if new_status is not None:
            trace.new_status = new_status
        if overdue_count is not None:
            trace.overdue_count = overdue_count
        if blocked_count is not None:
            trace.blocked_count = blocked_count
        if owner_workload_summary is not None:
            trace.owner_workload_summary = dict(owner_workload_summary)
        if snapshot_id is not None:
            trace.snapshot_id = snapshot_id
        if workbook_count is not None:
            trace.workbook_count = workbook_count
        if delivery_package_name is not None:
            trace.delivery_package_name = delivery_package_name
        if delivery_output_dir is not None:
            trace.delivery_output_dir = delivery_output_dir
        if generated_file_count is not None:
            trace.generated_file_count = generated_file_count
        if batch_name is not None:
            trace.batch_name = batch_name
        if file_count is not None:
            trace.file_count = file_count
        if group_count is not None:
            trace.group_count = group_count
        if changed_count is not None:
            trace.changed_count = changed_count
        if new_count is not None:
            trace.new_count = new_count
        if unchanged_count is not None:
            trace.unchanged_count = unchanged_count
        if removed_count is not None:
            trace.removed_count = removed_count
        if rerun_object_count is not None:
            trace.rerun_object_count = rerun_object_count
        if workbook_type is not None:
            trace.workbook_type = workbook_type
        if imported_count is not None:
            trace.imported_count = imported_count
        if invalid_count is not None:
            trace.invalid_count = invalid_count
        if changed_object_count is not None:
            trace.changed_object_count = changed_object_count
        if rerun_changed_only is not None:
            trace.rerun_changed_only = rerun_changed_only
        if domain_pack_name is not None:
            trace.domain_pack_name = domain_pack_name
        if template_name is not None:
            trace.template_name = template_name
        if domain_pack_match_confidence is not None:
            trace.domain_pack_match_confidence = domain_pack_match_confidence
        if applied_delivery_outputs is not None:
            trace.applied_delivery_outputs = list(applied_delivery_outputs)
        if intake_profile_name is not None:
            trace.intake_profile_name = intake_profile_name
        if intake_match_confidence is not None:
            trace.intake_match_confidence = intake_match_confidence
        if matched_sheet_name is not None:
            trace.matched_sheet_name = matched_sheet_name
        if unmapped_source_column_count is not None:
            trace.unmapped_source_column_count = unmapped_source_column_count
        if normalization_row_count is not None:
            trace.normalization_row_count = normalization_row_count
        if confirmation_template_name is not None:
            trace.confirmation_template_name = confirmation_template_name
        if template_match_confidence is not None:
            trace.template_match_confidence = template_match_confidence
        saved_trace = save_trace(trace)
        if saved_trace.session_id:
            append_trace_to_session(saved_trace.session_id, saved_trace.trace_id)
        return saved_trace

    @staticmethod
    def _build_tool_response(
        tool_name: str,
        status: str,
        message: str,
        result: dict[str, object] | list[object] | None,
        trace: ExecutionTrace,
    ) -> ToolCallResponse:
        return ToolCallResponse(
            tool_name=tool_name,
            status=status,
            message=message,
            result=result,
            trace_id=trace.trace_id,
            started_at=trace.started_at,
            finished_at=trace.finished_at,
        )

    def run_governance_profile(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run a named governance workflow profile directly."""
        tool_name = "run_governance_profile"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=self._optional_string(arguments, "profile_name"),
        )
        try:
            request = GovernanceTaskRequest.model_validate(arguments)
            response = run_governance_task(request)
            trace.profile_name = response.profile_name
            workflow_result = response.result
            review_queue = dict(workflow_result.quality_review_queue_summary or {})
            trace = self._finish_trace(
                trace,
                response.status,
                response.message,
                stages_executed=response.stages_executed,
                exported_files=dict(response.exported_files or {}),
                review_summary=self._extract_review_summary(response),
                field_rule_count=len(workflow_result.quality_rule_suggestions),
                cross_field_rule_count=len(workflow_result.cross_field_quality_rules),
                low_confidence_rule_count=int(
                    review_queue.get("low_confidence_rule_count", 0) or 0
                ),
                review_queue_summary=review_queue,
                readiness_score_count=len(workflow_result.readiness_scores),
                gap_count=len(workflow_result.governance_gaps),
                remediation_action_count=len(workflow_result.remediation_actions),
                work_package_name=(
                    workflow_result.governance_work_package.package_name
                    if workflow_result.governance_work_package is not None
                    else None
                ),
                backlog_item_count=len(workflow_result.governance_backlog_items),
                backlog_status_summary=(
                    workflow_result.backlog_summary.by_status
                    if workflow_result.backlog_summary is not None
                    else {}
                ),
                overdue_count=(
                    workflow_result.governance_portfolio_summary.overdue_count
                    if workflow_result.governance_portfolio_summary is not None
                    else None
                ),
                blocked_count=(
                    workflow_result.governance_portfolio_summary.blocked_count
                    if workflow_result.governance_portfolio_summary is not None
                    else None
                ),
                owner_workload_summary=(
                    workflow_result.governance_portfolio_summary.owner_workload
                    if workflow_result.governance_portfolio_summary is not None
                    else None
                ),
                snapshot_id=(
                    workflow_result.progress_snapshot.snapshot_id
                    if workflow_result.progress_snapshot is not None
                    else None
                ),
            )
            return self._build_tool_response(
                tool_name,
                response.status,
                response.message,
                response.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to run governance profile: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run governance profile.",
                None,
                trace,
            )

    def export_governance_reports(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Export governance reports from an existing workflow result."""
        tool_name = "export_governance_reports"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=self._optional_string(arguments, "profile_name"),
        )
        try:
            workflow_result = self._coerce_workflow_result(arguments)
            profile_name = self._resolve_export_profile_name(arguments, workflow_result)
            output_dir = self._optional_string(arguments, "output_dir") or str(
                DEFAULT_REPORT_OUTPUT_DIR
            )
            base_filename = self._optional_string(arguments, "base_filename") or build_report_base_filename(
                profile_name=profile_name
            )

            exported_files = export_all_reports(
                workflow_result,
                output_dir=output_dir,
                base_filename=base_filename,
            )
            trace.profile_name = profile_name
            trace = self._finish_trace(
                trace,
                "success",
                "Governance reports were exported successfully.",
                exported_files=exported_files,
                review_summary=(
                    workflow_result.review_summary.model_dump()
                    if workflow_result.review_summary is not None
                    else {}
                ),
                notes=[
                    f"Reports exported to {Path(output_dir).resolve()}",
                ],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance reports were exported successfully.",
                {
                    "profile_name": profile_name,
                    "output_dir": output_dir,
                    "base_filename": base_filename,
                    "exported_files": exported_files,
                },
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to export governance reports: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to export governance reports.",
                None,
                trace,
            )

    def export_confirmation_workbooks(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Export confirmation workbooks from a workflow result or local file."""
        tool_name = "export_confirmation_workbooks"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
        )
        try:
            workflow_result = self._optional_workflow_result(arguments)
            file_path = self._optional_string(arguments, "file_path")
            apply_review = bool(arguments.get("apply_review_replay", True))
            if workflow_result is None:
                if not file_path:
                    raise ValueError(
                        "Argument 'workflow_result' or 'file_path' is required."
                    )
                workflow_result = (
                    run_full_governance_backlog_package_from_file(file_path)
                    if apply_review
                    else run_governance_backlog_build_from_file(file_path)
                )
            output_dir = self._optional_string(arguments, "output_dir")
            base_name = self._optional_string(arguments, "base_filename") or self._optional_string(
                arguments,
                "base_name",
            )
            results = DeliveryService().build_confirmation_workbooks(
                workflow_result,
                output_dir=output_dir,
                base_name=base_name,
            )
            exported_files = {
                result.workbook_type: result.output_path for result in results
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Confirmation workbooks were exported successfully.",
                exported_files=exported_files,
                workbook_count=len(results),
                generated_file_count=len(exported_files),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Confirmation workbooks were exported successfully.",
                {
                    "confirmation_workbook_results": [
                        result.model_dump() for result in results
                    ],
                    "exported_files": exported_files,
                },
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to export confirmation workbooks: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to export confirmation workbooks.",
                None,
                trace,
            )

    def build_governance_delivery_package(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Build a local governance delivery package from workflow output."""
        tool_name = "build_governance_delivery_package"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
        )
        try:
            workflow_result = self._optional_workflow_result(arguments)
            file_path = self._optional_string(arguments, "file_path")
            apply_review = bool(arguments.get("apply_review_replay", True))
            if workflow_result is None:
                if not file_path:
                    raise ValueError(
                        "Argument 'workflow_result' or 'file_path' is required."
                    )
                workflow_result = (
                    run_full_governance_backlog_package_from_file(file_path)
                    if apply_review
                    else run_governance_backlog_build_from_file(file_path)
                )
            workflow_result = DeliveryService().build_governance_delivery_package(
                workflow_result,
                output_dir=self._optional_string(arguments, "output_dir"),
                base_name=self._optional_string(arguments, "base_filename")
                or self._optional_string(arguments, "base_name"),
            )

            package_result = workflow_result.governance_delivery_package_result
            manifest = workflow_result.governance_delivery_manifest
            generated_files = (
                dict(package_result.generated_files) if package_result is not None else {}
            )
            trace = self._finish_trace(
                trace,
                workflow_result.status,
                workflow_result.message,
                exported_files=generated_files,
                workbook_count=len(workflow_result.confirmation_workbook_results),
                delivery_package_name=(
                    package_result.package_name if package_result is not None else None
                ),
                delivery_output_dir=(
                    package_result.output_dir if package_result is not None else None
                ),
                generated_file_count=len(generated_files),
            )
            return self._build_tool_response(
                tool_name,
                workflow_result.status,
                workflow_result.message,
                {
                    "confirmation_workbook_results": [
                        result.model_dump()
                        for result in workflow_result.confirmation_workbook_results
                    ],
                    "governance_delivery_manifest": (
                        manifest.model_dump() if manifest is not None else None
                    ),
                    "governance_delivery_package_result": (
                        package_result.model_dump()
                        if package_result is not None
                        else None
                    ),
                },
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build governance delivery package: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build governance delivery package.",
                None,
                trace,
            )

    def _batch_arguments(self, arguments: dict[str, object]) -> tuple[list[str], str, str | None]:
        file_paths = [
            str(path)
            for path in arguments.get("file_paths", [])
            if str(path).strip()
        ] if isinstance(arguments.get("file_paths"), list) else []
        file_path = self._optional_string(arguments, "file_path")
        if file_path:
            file_paths.append(file_path)
        if not file_paths:
            raise ValueError("Argument 'file_paths' or 'file_path' is required.")
        group_by = self._optional_string(arguments, "group_by") or "system_name"
        batch_name = self._optional_string(arguments, "batch_name") or self._optional_string(
            arguments,
            "base_filename",
        )
        return file_paths, group_by, batch_name

    def run_batch_governance(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run multi-file batch governance."""
        tool_name = "run_batch_governance"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_paths, group_by, batch_name = self._batch_arguments(arguments)
            result = run_batch_governance_workflow_from_files(
                file_paths,
                group_by=group_by,
                changed_only=False,
                batch_name=batch_name,
            )
            summary = result.incremental_diff_summary
            rerun_scope = result.rerun_scope_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                batch_name=rerun_scope.get("batch_name") if rerun_scope else batch_name,
                file_count=len(file_paths),
                group_count=len(result.batch_group_results),
                changed_count=summary.changed_count if summary else None,
                new_count=summary.new_count if summary else None,
                unchanged_count=summary.unchanged_count if summary else None,
                removed_count=summary.removed_count if summary else None,
                rerun_object_count=rerun_scope.get("rerun_object_count") if rerun_scope else None,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to run batch governance: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run batch governance.",
                None,
                trace,
            )

    def run_incremental_rerun(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run changed-only batch governance using local snapshots."""
        tool_name = "run_incremental_rerun"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_paths, group_by, batch_name = self._batch_arguments(arguments)
            result = run_batch_governance_workflow_from_files(
                file_paths,
                group_by=group_by,
                changed_only=True,
                batch_name=batch_name,
            )
            summary = result.incremental_diff_summary
            rerun_scope = result.rerun_scope_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                batch_name=rerun_scope.get("batch_name") if rerun_scope else batch_name,
                file_count=len(file_paths),
                group_count=len(result.batch_group_results),
                changed_count=summary.changed_count if summary else None,
                new_count=summary.new_count if summary else None,
                unchanged_count=summary.unchanged_count if summary else None,
                removed_count=summary.removed_count if summary else None,
                rerun_object_count=rerun_scope.get("rerun_object_count") if rerun_scope else None,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to run incremental rerun: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run incremental rerun.",
                None,
                trace,
            )

    def compare_governance_snapshots(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Compare the latest stored snapshot with itself or return latest snapshot metadata."""
        tool_name = "compare_governance_snapshots"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            batch_name = self._optional_string(arguments, "batch_name") or "default_batch_governance"
            latest = load_latest_batch_snapshot(batch_name)
            snapshots = list_batch_snapshots(batch_name)
            fingerprints = latest.get("fingerprints", []) if latest else []
            diff_items = IncrementalDiffService().compare_fingerprints(
                fingerprints,
                fingerprints,
            )
            summary = IncrementalDiffService.build_incremental_diff_summary(diff_items)
            latest_payload = None
            if latest:
                latest_payload = dict(latest)
                latest_payload["fingerprints"] = [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in fingerprints
                ]
            result = {
                "batch_name": batch_name,
                "latest_snapshot": latest_payload,
                "snapshots": snapshots,
                "incremental_diff_items": [
                    item.model_dump() for item in diff_items
                ],
                "incremental_diff_summary": summary.model_dump(),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance snapshots were compared successfully.",
                batch_name=batch_name,
                changed_count=summary.changed_count,
                new_count=summary.new_count,
                unchanged_count=summary.unchanged_count,
                removed_count=summary.removed_count,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance snapshots were compared successfully.",
                result,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to compare governance snapshots: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to compare governance snapshots.",
                None,
                trace,
            )

    def import_confirmation_workbook(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Import and merge one filled confirmation workbook."""
        tool_name = "import_confirmation_workbook"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            workbook_type = self._optional_string(arguments, "workbook_type") or "mapping_confirmation"
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            result = WorkflowEngine().import_confirmation_workbook_and_merge(
                file_path,
                workbook_type,
            )
            summary = result.workbook_import_summaries[0] if result.workbook_import_summaries else None
            changed_summary = result.roundtrip_changed_objects_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                workbook_type=workbook_type,
                imported_count=summary.imported_count if summary else None,
                invalid_count=summary.invalid_count if summary else None,
                changed_object_count=int(changed_summary.get("changed_object_count", 0) or 0),
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to import confirmation workbook: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to import confirmation workbook.",
                None,
                trace,
            )

    def import_confirmation_and_rerun(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Import confirmation workbook and prepare changed-object rerun scope."""
        tool_name = "import_confirmation_and_rerun"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            workbook_type = self._optional_string(arguments, "workbook_type") or "mapping_confirmation"
            rerun_changed_only = bool(arguments.get("rerun_changed_only", True))
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            result = WorkflowEngine().import_confirmation_workbook_and_rerun(
                file_path,
                workbook_type,
                rerun_changed_only=rerun_changed_only,
            )
            summary = result.workbook_import_summaries[0] if result.workbook_import_summaries else None
            changed_summary = result.roundtrip_changed_objects_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                workbook_type=workbook_type,
                imported_count=summary.imported_count if summary else None,
                invalid_count=summary.invalid_count if summary else None,
                changed_object_count=int(changed_summary.get("changed_object_count", 0) or 0),
                rerun_changed_only=rerun_changed_only,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to import confirmation workbook and rerun: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to import confirmation workbook and rerun.",
                None,
                trace,
            )

    def list_domain_governance_packs(self, arguments: dict[str, object]) -> ToolCallResponse:
        """List enabled domain governance packs."""
        tool_name = "list_domain_governance_packs"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            packs = [pack.model_dump() for pack in list_enabled_domain_packs()]
            trace = self._finish_trace(trace, "success", f"Listed {len(packs)} domain governance packs.")
            return self._build_tool_response(tool_name, "success", "Domain governance packs listed.", {"packs": packs}, trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def list_project_templates(self, arguments: dict[str, object]) -> ToolCallResponse:
        """List enabled project templates."""
        tool_name = "list_project_templates"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            templates = [template.model_dump() for template in list_enabled_project_templates()]
            trace = self._finish_trace(trace, "success", f"Listed {len(templates)} project templates.")
            return self._build_tool_response(tool_name, "success", "Project templates listed.", {"templates": templates}, trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def list_delivery_template_profiles(self, arguments: dict[str, object]) -> ToolCallResponse:
        """List enabled enterprise delivery templates and bundle variants."""
        tool_name = "list_delivery_template_profiles"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            profiles = [
                profile.model_dump()
                for profile in list_enabled_delivery_template_profiles()
            ]
            variants = list_enabled_delivery_bundle_variants()
            trace = self._finish_trace(
                trace,
                "success",
                f"Listed {len(profiles)} delivery templates and {len(variants)} bundle variants.",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Delivery template profiles listed.",
                {
                    "profiles": profiles,
                    "bundle_variants": variants,
                },
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def match_domain_governance_pack(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Match a domain governance pack from text."""
        tool_name = "match_domain_governance_pack"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            match = DomainPackMatcher().match_domain_pack_from_text(self._require_text(arguments))
            trace = self._finish_trace(
                trace,
                "success",
                match.message or "Domain governance pack matched.",
                domain_pack_name=match.matched_pack_name,
                domain_pack_match_confidence=match.confidence,
            )
            return self._build_tool_response(tool_name, "success", trace.message or "Matched.", match.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def run_project_template(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run a project template with optional domain pack override."""
        tool_name = "run_project_template"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name="run_project_template",
        )
        try:
            template_name = self._optional_string(arguments, "template_name")
            file_path = self._optional_string(arguments, "file_path")
            if not template_name or not file_path:
                raise ValueError("Arguments 'template_name' and 'file_path' are required.")
            result = ProjectTemplateService().run_project_template(
                template_name=template_name,
                file_path=file_path,
                domain_pack_name=self._optional_string(arguments, "domain_pack_name"),
                output_dir=self._optional_string(arguments, "output_dir"),
            )
            template_result = result.project_template_result
            applied_outputs: list[str] = []
            selected_pack = None
            if template_result is not None:
                selected_pack = template_result.selected_domain_pack
                outputs = template_result.applied_defaults.get("default_outputs", [])
                if isinstance(outputs, list):
                    applied_outputs = [str(item) for item in outputs]
            match_confidence = result.domain_pack_match.confidence if result.domain_pack_match else None
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                domain_pack_name=selected_pack,
                template_name=template_name,
                domain_pack_match_confidence=match_confidence,
                applied_delivery_outputs=applied_outputs,
            )
            return self._build_tool_response(tool_name, result.status, result.message, result.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc), template_name=self._optional_string(arguments, "template_name"))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def diagnose_metadata_intake_template(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Diagnose a structured metadata intake template."""
        tool_name = "diagnose_metadata_intake_template"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            result = IntakeAdapterService().diagnose_intake_template(
                file_path,
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            trace = self._finish_trace(
                trace,
                "success",
                result.message or "Metadata intake template diagnosed.",
                intake_profile_name=result.matched_profile_name,
                intake_match_confidence=result.confidence,
                matched_sheet_name=result.matched_sheet_name,
            )
            return self._build_tool_response(tool_name, "success", trace.message or "Diagnosed.", result.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def normalize_metadata_input(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Normalize an enterprise metadata intake file."""
        tool_name = "normalize_metadata_input"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            result = IntakeAdapterService().normalize_metadata_input(
                file_path,
                profile_name=self._optional_string(arguments, "intake_profile_name"),
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            unmapped_count = (
                len(result.mapping_result.unmapped_source_columns)
                if result.mapping_result is not None
                else None
            )
            trace = self._finish_trace(
                trace,
                result.status,
                result.message or "Metadata input normalized.",
                intake_profile_name=result.profile_name,
                unmapped_source_column_count=unmapped_count,
                normalization_row_count=result.row_count,
            )
            return self._build_tool_response(tool_name, result.status, result.message or "Normalized.", result.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def run_governance_with_intake_profile(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Normalize intake metadata and run a governance workflow."""
        tool_name = "run_governance_with_intake_profile"
        profile_name = self._optional_string(arguments, "profile_name") or "metadata_diagnosis_only"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=profile_name,
        )
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            result = WorkflowEngine().run_governance_with_intake_profile(
                file_path,
                profile_name=profile_name,
                intake_profile_name=self._optional_string(arguments, "intake_profile_name"),
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            mapping = result.intake_mapping_result
            normalization = result.intake_normalization_result
            match = result.intake_match_result
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                intake_profile_name=normalization.profile_name if normalization else None,
                intake_match_confidence=match.confidence if match else None,
                matched_sheet_name=match.matched_sheet_name if match else None,
                unmapped_source_column_count=(
                    len(mapping.unmapped_source_columns) if mapping else None
                ),
                normalization_row_count=normalization.row_count if normalization else None,
            )
            return self._build_tool_response(tool_name, result.status, result.message, result.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def diagnose_confirmation_template(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Diagnose a confirmation workbook template."""
        tool_name = "diagnose_confirmation_template"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            result = ConfirmationWorkbookImporter().diagnose_confirmation_template(
                file_path,
                workbook_type=self._optional_string(arguments, "workbook_type"),
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            trace = self._finish_trace(
                trace,
                "success",
                result.message or "Confirmation template diagnosed.",
                workbook_type=result.workbook_type,
                confirmation_template_name=result.matched_template_name,
                template_match_confidence=result.confidence,
                matched_sheet_name=result.matched_sheet_name,
            )
            return self._build_tool_response(tool_name, "success", trace.message or "Diagnosed.", result.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def import_confirmation_with_template(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Import and merge confirmation workbook using a template profile."""
        tool_name = "import_confirmation_with_template"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            rerun_changed_only = bool(arguments.get("rerun_changed_only", False))
            if rerun_changed_only:
                result = WorkflowEngine().import_confirmation_with_template_and_rerun(
                    file_path,
                    template_name=self._optional_string(arguments, "confirmation_template_name"),
                    workbook_type=self._optional_string(arguments, "workbook_type"),
                    sheet_name=self._optional_string(arguments, "sheet_name"),
                    rerun_changed_only=True,
                )
            else:
                result = WorkflowEngine().import_confirmation_with_template(
                    file_path,
                    template_name=self._optional_string(arguments, "confirmation_template_name"),
                    workbook_type=self._optional_string(arguments, "workbook_type"),
                    sheet_name=self._optional_string(arguments, "sheet_name"),
                )
            summary = result.workbook_import_summaries[0] if result.workbook_import_summaries else None
            match = result.confirmation_template_match_result
            mapping = result.confirmation_template_mapping_result
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                workbook_type=summary.workbook_type if summary else None,
                confirmation_template_name=(
                    mapping.template_name if mapping else (match.matched_template_name if match else None)
                ),
                template_match_confidence=match.confidence if match else None,
                matched_sheet_name=match.matched_sheet_name if match else None,
                imported_count=summary.imported_count if summary else None,
                invalid_count=summary.invalid_count if summary else None,
                rerun_changed_only=rerun_changed_only,
            )
            return self._build_tool_response(tool_name, result.status, result.message, result.model_dump(), trace)
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def recommend_quality_rules(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run the workflow chain up to quality rule recommendation."""
        tool_name = "recommend_quality_rules"
        apply_review_replay = bool(arguments.get("apply_review_replay", False))
        default_profile = (
            "diagnosis_mapping_stg_quality_with_review"
            if apply_review_replay
            else "diagnosis_mapping_stg_quality"
        )
        profile_name = self._optional_string(arguments, "profile_name") or default_profile
        if apply_review_replay and profile_name == "diagnosis_mapping_stg_quality":
            profile_name = "diagnosis_mapping_stg_quality_with_review"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=profile_name,
        )
        try:
            request = GovernanceTaskRequest(
                file_path=self._optional_string(arguments, "file_path"),
                profile_name=profile_name,
                apply_review_replay=apply_review_replay,
                export_reports=bool(arguments.get("export_reports", False)),
                preferred_result_mode=self._optional_string(
                    arguments, "preferred_result_mode"
                ),
                output_dir=self._optional_string(arguments, "output_dir"),
                base_filename=self._optional_string(arguments, "base_filename"),
            )
            response = run_governance_task(request)
            trace.profile_name = response.profile_name
            trace = self._finish_trace(
                trace,
                response.status,
                response.message,
                stages_executed=response.stages_executed,
                exported_files=dict(response.exported_files or {}),
                review_summary=self._extract_review_summary(response),
            )
            return self._build_tool_response(
                tool_name,
                response.status,
                response.message,
                response.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to recommend quality rules: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to recommend quality rules.",
                None,
                trace,
            )

    def recommend_quality_intelligence(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Run the quality intelligence workflow with field and cross-field rules."""
        tool_name = "recommend_quality_intelligence"
        profile_name = (
            self._optional_string(arguments, "profile_name")
            or "diagnosis_mapping_stg_quality"
        )
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=profile_name,
            operation="quality_intelligence",
        )
        try:
            request = GovernanceTaskRequest(
                file_path=self._optional_string(arguments, "file_path"),
                profile_name=profile_name,
                apply_review_replay=bool(arguments.get("apply_review_replay", False)),
                export_reports=bool(arguments.get("export_reports", False)),
                preferred_result_mode="quality",
                output_dir=self._optional_string(arguments, "output_dir"),
                base_filename=self._optional_string(arguments, "base_filename"),
            )
            response = run_governance_task(request)
            workflow_result = response.result
            review_queue = dict(workflow_result.quality_review_queue_summary or {})
            low_confidence_count = int(review_queue.get("low_confidence_rule_count", 0) or 0)
            trace = self._finish_trace(
                trace,
                response.status,
                response.message,
                stages_executed=response.stages_executed,
                exported_files=dict(response.exported_files or {}),
                operation="quality_intelligence",
                field_rule_count=len(workflow_result.quality_rule_suggestions),
                cross_field_rule_count=len(workflow_result.cross_field_quality_rules),
                low_confidence_rule_count=low_confidence_count,
                review_queue_summary=review_queue,
            )
            return self._build_tool_response(
                tool_name,
                response.status,
                response.message,
                response.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to recommend quality intelligence: {exc}",
                operation="quality_intelligence",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to recommend quality intelligence.",
                None,
                trace,
            )

    def review_quality_rules(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Review quality rule suggestions and build confirmed quality rules."""
        tool_name = "review_quality_rules"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="quality_review",
        )
        try:
            workflow_result = self._optional_workflow_result(arguments)
            suggestions = self._coerce_quality_rule_suggestions(
                arguments.get("quality_rule_suggestions")
            )
            cross_field_rules = self._coerce_cross_field_quality_rules(
                arguments.get("cross_field_quality_rules")
            )
            if not suggestions and workflow_result is not None:
                suggestions = list(workflow_result.quality_rule_suggestions)
            if not cross_field_rules and workflow_result is not None:
                cross_field_rules = list(workflow_result.cross_field_quality_rules)
            suggestions = suggestions + self._cross_field_rules_as_suggestions(
                cross_field_rules
            )
            if not suggestions:
                raise ValueError(
                    "quality_rule_suggestions, cross_field_quality_rules, or a workflow_result with suggestions is required."
                )

            records = self._coerce_quality_review_records(arguments.get("records"))
            if not records:
                review_inputs = arguments.get("review_inputs")
                if review_inputs is None:
                    review_inputs = {}
                if not isinstance(review_inputs, dict):
                    raise ValueError("review_inputs must be an object keyed by rule id.")
                records = build_quality_rule_review_records_from_results(
                    suggestions,
                    review_inputs,
                    source=self._optional_string(arguments, "source") or "tool",
                )

            reviewed_suggestions, applied_count, _ = apply_quality_rule_overrides_to_results(
                suggestions,
                records,
            )
            confirmed_rules = build_confirmed_quality_rules(suggestions, records)
            summary = summarize_quality_rule_review_records(
                records,
                confirmed_count=len(confirmed_rules),
            )
            saved_payload = None
            if bool(arguments.get("save_overrides", False)):
                saved_payload = save_quality_rule_review_records(records)

            result_payload = {
                "review_records": [record.model_dump() for record in records],
                "reviewed_quality_rule_suggestions": [
                    suggestion.model_dump() for suggestion in reviewed_suggestions
                ],
                "confirmed_quality_rules": [
                    rule.model_dump() for rule in confirmed_rules
                ],
                "quality_rule_review_summary": summary,
                "applied_quality_review_count": applied_count,
                "saved": saved_payload,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Quality rules were reviewed and confirmed results were built.",
                review_summary=summary,
                operation="quality_review",
                confirmed_rule_count=len(confirmed_rules),
                field_rule_count=sum(1 for rule in suggestions if rule.rule_scope == "field"),
                cross_field_rule_count=sum(
                    1 for rule in suggestions if rule.rule_scope == "cross_field"
                ),
                low_confidence_rule_count=sum(
                    1
                    for rule in suggestions
                    if rule.confidence is not None and rule.confidence <= 0.4
                ),
                review_queue_summary=summarize_review_queue(suggestions),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Quality rules were reviewed and confirmed results were built.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to review quality rules: {exc}",
                operation="quality_review",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to review quality rules.",
                None,
                trace,
            )

    def batch_review_quality_rules(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Build batch quality rule review records from simple local policies."""
        tool_name = "batch_review_quality_rules"
        action = (self._optional_string(arguments, "action") or "").lower()
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="quality_batch_review",
        )
        try:
            workflow_result = self._optional_workflow_result(arguments)
            suggestions = self._coerce_quality_rule_suggestions(
                arguments.get("quality_rule_suggestions")
            )
            cross_field_rules = self._coerce_cross_field_quality_rules(
                arguments.get("cross_field_quality_rules")
            )
            if workflow_result is not None:
                if not suggestions:
                    suggestions = list(workflow_result.quality_rule_suggestions)
                if not cross_field_rules:
                    cross_field_rules = list(workflow_result.cross_field_quality_rules)
            suggestions = suggestions + self._cross_field_rules_as_suggestions(
                cross_field_rules
            )
            if not suggestions:
                raise ValueError("No quality rules were provided for batch review.")

            if action == "accept_by_rule_type":
                records = bulk_accept_by_rule_type(
                    suggestions,
                    self._optional_string(arguments, "rule_type") or "",
                    source="tool_batch_review",
                )
            elif action == "accept_by_table":
                records = bulk_accept_by_table(
                    suggestions,
                    self._optional_string(arguments, "table_name") or "",
                    source="tool_batch_review",
                )
            elif action == "mark_low_confidence_manual_review":
                records = bulk_mark_manual_review_by_low_confidence(
                    suggestions,
                    threshold=float(arguments.get("confidence_threshold", 0.4)),
                    source="tool_batch_review",
                )
            else:
                raise ValueError(
                    "action must be accept_by_rule_type, accept_by_table, or mark_low_confidence_manual_review."
                )

            summary = summarize_review_queue(suggestions)
            saved_payload = None
            if bool(arguments.get("save_overrides", False)):
                saved_payload = save_quality_rule_review_records(records)
            result_payload = {
                "review_records": [record.model_dump() for record in records],
                "review_queue_summary": summary,
                "saved": saved_payload,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Batch quality rule review records were built successfully.",
                operation="quality_batch_review",
                field_rule_count=int(summary.get("field_rule_count", 0) or 0),
                cross_field_rule_count=int(summary.get("cross_field_rule_count", 0) or 0),
                low_confidence_rule_count=int(summary.get("low_confidence_rule_count", 0) or 0),
                review_queue_summary=summary,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Batch quality rule review records were built successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build batch review records: {exc}",
                operation="quality_batch_review",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build batch review records.",
                None,
                trace,
            )

    def export_confirmed_quality_rules(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Export confirmed quality rules to a local rules package."""
        tool_name = "export_confirmed_quality_rules"
        export_format = (
            self._optional_string(arguments, "export_format") or "json"
        ).lower()
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="rule_export",
        )
        try:
            confirmed_rules = self._coerce_confirmed_quality_rules(
                arguments.get("confirmed_quality_rules")
            )
            workflow_result = self._optional_workflow_result(arguments)
            if not confirmed_rules and workflow_result is not None:
                confirmed_rules = list(workflow_result.confirmed_quality_rules)

            file_path = self._optional_string(arguments, "file_path")
            if not confirmed_rules and file_path:
                apply_review_replay = bool(arguments.get("apply_review_replay", True))
                workflow_result = (
                    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(file_path)
                    if apply_review_replay
                    else run_p0_plus_mapping_plus_stg_plus_quality_from_file(file_path)
                )
                confirmed_rules = list(workflow_result.confirmed_quality_rules)
                if not confirmed_rules and apply_review_replay:
                    quality_overrides = load_quality_rule_overrides()
                    confirmed_rules = build_confirmed_quality_rules(
                        workflow_result.quality_rule_suggestions,
                        quality_overrides,
                    )

            output_dir = Path(
                self._optional_string(arguments, "output_dir")
                or (Path(__file__).resolve().parents[3] / "outputs" / "rule_exports")
            )
            base_filename = (
                self._optional_string(arguments, "base_filename")
                or f"confirmed_quality_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            adapter = RuleExportAdapter()
            results = []
            normalized_format = {
                "json": "custom_json",
                "custom_json": "custom_json",
                "dbt": "dbt_yaml",
                "dbt_yaml": "dbt_yaml",
                "yaml": "dbt_yaml",
            }.get(export_format, export_format)

            if normalized_format in {"custom_json", "both"}:
                results.append(
                    adapter.export_custom_json_rules(
                        confirmed_rules,
                        str(output_dir / f"{base_filename}.json"),
                    )
                )
            if normalized_format in {"dbt_yaml", "both"}:
                results.append(
                    adapter.export_dbt_tests_yaml(
                        confirmed_rules,
                        str(output_dir / f"{base_filename}_dbt.yml"),
                    )
                )
            if not results:
                raise ValueError(
                    "export_format must be one of json, custom_json, dbt, dbt_yaml, yaml, or both."
                )

            result_payload = {
                "confirmed_rule_count": len(confirmed_rules),
                "rule_export_results": [result.model_dump() for result in results],
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Confirmed quality rules were exported successfully.",
                exported_files={
                    result.export_format: result.output_path for result in results
                },
                operation="rule_export",
                export_format=normalized_format,
                exported_rule_count=sum(result.rule_count for result in results),
                confirmed_rule_count=len(confirmed_rules),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Confirmed quality rules were exported successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to export confirmed quality rules: {exc}",
                operation="rule_export",
                export_format=export_format,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to export confirmed quality rules.",
                None,
                trace,
            )

    def _resolve_execution_ready_package_from_arguments(
        self,
        arguments: dict[str, object],
    ) -> tuple[ExecutionReadyPackage, WorkflowResult | None, list[ConfirmedQualityRule]]:
        """Resolve or build an execution-ready package from tool arguments."""
        package = self._coerce_execution_ready_package(
            arguments.get("execution_ready_package", arguments.get("package"))
        )
        workflow_result = self._optional_workflow_result(arguments)
        confirmed_rules = self._coerce_confirmed_quality_rules(
            arguments.get("confirmed_quality_rules")
        )

        if package is not None:
            return package, workflow_result, confirmed_rules

        if workflow_result is not None and workflow_result.execution_ready_package is not None:
            return (
                workflow_result.execution_ready_package,
                workflow_result,
                list(workflow_result.confirmed_quality_rules),
            )

        if not confirmed_rules and workflow_result is not None:
            confirmed_rules = list(workflow_result.confirmed_quality_rules)

        file_path = self._optional_string(arguments, "file_path")
        if not confirmed_rules and file_path:
            apply_review_replay = bool(arguments.get("apply_review_replay", True))
            workflow_result = (
                run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
                    file_path
                )
                if apply_review_replay
                else run_p0_plus_mapping_plus_stg_plus_quality_from_file(file_path)
            )
            if workflow_result.execution_ready_package is not None:
                return (
                    workflow_result.execution_ready_package,
                    workflow_result,
                    list(workflow_result.confirmed_quality_rules),
                )
            confirmed_rules = list(workflow_result.confirmed_quality_rules)

        if not confirmed_rules and "confirmed_quality_rules" not in arguments:
            raise ValueError(
                "An execution_ready_package, confirmed_quality_rules, workflow_result, or file_path is required."
            )

        profile_name = (
            self._optional_string(arguments, "profile_name")
            or (
                workflow_result.execution_ready_package.source_profile
                if workflow_result is not None
                and workflow_result.execution_ready_package is not None
                else None
            )
            or "quality_package_only_from_confirmed"
        )
        builder = ExecutionPackageBuilder()
        return (
            builder.build_package(
                confirmed_rules,
                profile_name=profile_name,
                trace_metadata={"tool_name": "build_execution_ready_package"},
            ),
            workflow_result,
            confirmed_rules,
        )

    def build_execution_ready_package(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Build an execution-ready governance package from confirmed quality rules."""
        tool_name = "build_execution_ready_package"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="execution_package_build",
        )
        try:
            package, workflow_result, confirmed_rules = (
                self._resolve_execution_ready_package_from_arguments(arguments)
            )
            summary = ExecutionPackageBuilder.summarize_package(package)
            result_payload = {
                "execution_ready_package": package.model_dump(),
                "execution_package_summary": summary,
                "confirmed_rule_count": len(confirmed_rules),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Execution-ready governance package was built successfully.",
                stages_executed=(
                    ["quality_review_replay", "execution_package_build"]
                    if workflow_result is not None
                    else ["execution_package_build"]
                ),
                operation="execution_package_build",
                confirmed_rule_count=len(confirmed_rules),
                package_id=package.package_id,
                package_rule_count=package.rule_count,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Execution-ready governance package was built successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build execution-ready package: {exc}",
                operation="execution_package_build",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build execution-ready package.",
                None,
                trace,
            )

    def export_execution_ready_package(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Export an execution-ready governance package."""
        tool_name = "export_execution_ready_package"
        export_format = (
            self._optional_string(arguments, "export_format") or "json"
        ).lower()
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="execution_package_export",
        )
        try:
            package, _, confirmed_rules = self._resolve_execution_ready_package_from_arguments(
                arguments
            )
            output_dir = Path(
                self._optional_string(arguments, "output_dir")
                or (
                    Path(__file__).resolve().parents[3]
                    / "outputs"
                    / "execution_packages"
                )
            )
            base_filename = (
                self._optional_string(arguments, "base_filename")
                or f"execution_ready_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            normalized_format = {
                "json": "package_json",
                "package_json": "package_json",
                "manifest": "package_manifest",
                "package_manifest": "package_manifest",
                "dbt": "dbt_yaml",
                "dbt_yaml": "dbt_yaml",
                "yaml": "dbt_yaml",
                "all": "all",
                "both": "all",
            }.get(export_format, export_format)

            adapter = RuleExportAdapter()
            export_results: list[ExecutionPackageExportResult] = []
            if normalized_format in {"package_json", "all"}:
                export_results.append(
                    adapter.export_execution_ready_package_json(
                        package,
                        str(output_dir / f"{base_filename}.json"),
                    )
                )
            if normalized_format in {"package_manifest", "all"}:
                export_results.append(
                    adapter.export_execution_ready_package_manifest(
                        package,
                        str(output_dir / f"{base_filename}_manifest.json"),
                    )
                )
            if normalized_format in {"dbt_yaml", "all"}:
                dbt_result = adapter.export_dbt_tests_yaml(
                    package,
                    str(output_dir / f"{base_filename}_dbt.yml"),
                )
                export_results.append(
                    ExecutionPackageExportResult(
                        export_format=dbt_result.export_format,
                        output_path=dbt_result.output_path,
                        package_id=package.package_id,
                        rule_count=dbt_result.rule_count,
                        status=dbt_result.status,
                        message=dbt_result.message,
                    )
                )
            if not export_results:
                raise ValueError(
                    "export_format must be one of json, package_json, manifest, package_manifest, dbt, dbt_yaml, yaml, all, or both."
                )

            result_payload = {
                "package_id": package.package_id,
                "package_rule_count": package.rule_count,
                "confirmed_rule_count": len(confirmed_rules),
                "execution_package_export_results": [
                    result.model_dump() for result in export_results
                ],
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Execution-ready governance package was exported successfully.",
                exported_files={
                    result.export_format: result.output_path
                    for result in export_results
                },
                operation="execution_package_export",
                export_format=normalized_format,
                confirmed_rule_count=len(confirmed_rules),
                package_id=package.package_id,
                package_rule_count=package.rule_count,
                exported_package_path=export_results[0].output_path,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Execution-ready governance package was exported successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to export execution-ready package: {exc}",
                operation="execution_package_export",
                export_format=export_format,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to export execution-ready package.",
                None,
                trace,
            )

    def _resolve_readiness_result_from_arguments(
        self,
        arguments: dict[str, object],
        *,
        full_work_package: bool,
    ) -> WorkflowResult:
        """Resolve or compute readiness outputs from a workflow result or file path."""
        workflow_result = self._optional_workflow_result(arguments)
        file_path = self._optional_string(arguments, "file_path")
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
                self._optional_string(arguments, "package_name")
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

    def _maybe_export_governance_work_package(
        self,
        arguments: dict[str, object],
        workflow_result: WorkflowResult,
    ) -> dict[str, str]:
        """Write the governance work package as a local JSON asset when requested."""
        work_package = workflow_result.governance_work_package
        if work_package is None:
            return {}
        should_export = bool(arguments.get("export_package", False)) or bool(
            self._optional_string(arguments, "output_dir")
        )
        if not should_export:
            return {}

        output_dir = Path(
            self._optional_string(arguments, "output_dir")
            or (Path(__file__).resolve().parents[3] / "outputs" / "governance_work_packages")
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        base_filename = (
            self._optional_string(arguments, "base_filename")
            or f"governance_work_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        output_path = output_dir / f"{base_filename}.json"
        output_path.write_text(
            json.dumps(work_package.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"governance_work_package": str(output_path)}

    def assess_governance_readiness(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Assess governance readiness and classify gaps from local workflow output."""
        tool_name = "assess_governance_readiness"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="readiness_assessment",
        )
        try:
            workflow_result = self._resolve_readiness_result_from_arguments(
                arguments,
                full_work_package=False,
            )
            result_payload = {
                "readiness_scores": [
                    score.model_dump() for score in workflow_result.readiness_scores
                ],
                "governance_gaps": [
                    gap.model_dump() for gap in workflow_result.governance_gaps
                ],
                "readiness_summary": dict(workflow_result.readiness_summary or {}),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance readiness assessment was generated successfully.",
                operation="readiness_assessment",
                readiness_score_count=len(workflow_result.readiness_scores),
                gap_count=len(workflow_result.governance_gaps),
                remediation_action_count=len(workflow_result.remediation_actions),
                work_package_name=(
                    workflow_result.governance_work_package.package_name
                    if workflow_result.governance_work_package is not None
                    else None
                ),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance readiness assessment was generated successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to assess governance readiness: {exc}",
                operation="readiness_assessment",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to assess governance readiness.",
                None,
                trace,
            )

    def build_governance_work_package(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Build an exportable governance work package for remediation planning."""
        tool_name = "build_governance_work_package"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="remediation_planning",
        )
        try:
            workflow_result = self._resolve_readiness_result_from_arguments(
                arguments,
                full_work_package=True,
            )
            exported_files = self._maybe_export_governance_work_package(
                arguments,
                workflow_result,
            )
            work_package_payload = (
                workflow_result.governance_work_package.model_dump()
                if workflow_result.governance_work_package is not None
                else None
            )
            result_payload = {
                "readiness_scores": [
                    score.model_dump() for score in workflow_result.readiness_scores
                ],
                "governance_gaps": [
                    gap.model_dump() for gap in workflow_result.governance_gaps
                ],
                "remediation_actions": [
                    action.model_dump()
                    for action in workflow_result.remediation_actions
                ],
                "governance_work_package": work_package_payload,
                "readiness_summary": dict(workflow_result.readiness_summary or {}),
                "exported_files": exported_files,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance work package was built successfully.",
                exported_files=exported_files,
                operation="remediation_planning",
                readiness_score_count=len(workflow_result.readiness_scores),
                gap_count=len(workflow_result.governance_gaps),
                remediation_action_count=len(workflow_result.remediation_actions),
                work_package_name=(
                    workflow_result.governance_work_package.package_name
                    if workflow_result.governance_work_package is not None
                    else None
                ),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance work package was built successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build governance work package: {exc}",
                operation="remediation_planning",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build governance work package.",
                None,
                trace,
            )

    def _resolve_backlog_items_from_arguments(
        self,
        arguments: dict[str, object],
    ) -> tuple[list[GovernanceBacklogItem], WorkflowResult | None]:
        """Resolve or build backlog items from tool arguments."""
        provided_items = self._coerce_governance_backlog_items(
            arguments.get("governance_backlog_items")
        )
        if provided_items:
            return provided_items, self._optional_workflow_result(arguments)

        workflow_result = self._optional_workflow_result(arguments)
        file_path = self._optional_string(arguments, "file_path")
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
            remediation_actions = self._coerce_remediation_actions(
                arguments.get("remediation_actions")
            )
            if not remediation_actions:
                return [], None
            items, _ = service.builder.build_backlog(remediation_actions)
            return items, None

        if not workflow_result.remediation_actions:
            workflow_result = self._resolve_readiness_result_from_arguments(
                {"workflow_result": workflow_result},
                full_work_package=True,
            )
        items, summary = service.build_backlog_from_work_package(
            workflow_result=workflow_result
        )
        workflow_result.governance_backlog_items = items
        workflow_result.backlog_summary = summary
        return items, workflow_result

    def build_governance_backlog(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Build local governance backlog items from remediation actions."""
        tool_name = "build_governance_backlog"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="backlog_build",
        )
        try:
            service = GovernanceBacklogTrackingService()
            items, workflow_result = self._resolve_backlog_items_from_arguments(arguments)
            summary = service.summarize_backlog(items)
            persisted = None
            if bool(arguments.get("persist", False)):
                persisted = service.persist_backlog_items(
                    items,
                    append=bool(arguments.get("append", True)),
                )
            result_payload = {
                "governance_backlog_items": [item.model_dump() for item in items],
                "backlog_summary": summary.model_dump(),
                "persisted": persisted,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance backlog was built successfully.",
                stages_executed=(
                    ["remediation_planning", "backlog_build"]
                    if workflow_result is not None
                    else ["backlog_build"]
                ),
                operation="backlog_build",
                backlog_item_count=len(items),
                backlog_status_summary=summary.by_status,
                readiness_score_count=(
                    len(workflow_result.readiness_scores)
                    if workflow_result is not None
                    else None
                ),
                gap_count=(
                    len(workflow_result.governance_gaps)
                    if workflow_result is not None
                    else None
                ),
                remediation_action_count=(
                    len(workflow_result.remediation_actions)
                    if workflow_result is not None
                    else None
                ),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance backlog was built successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build governance backlog: {exc}",
                operation="backlog_build",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build governance backlog.",
                None,
                trace,
            )

    def update_governance_backlog_status(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Update one persisted backlog item status."""
        tool_name = "update_governance_backlog_status"
        backlog_id = self._optional_string(arguments, "backlog_id") or ""
        new_status = self._optional_string(arguments, "new_status") or ""
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="backlog_status_update",
        )
        try:
            if not backlog_id:
                raise ValueError("Argument 'backlog_id' is required.")
            if not new_status:
                raise ValueError("Argument 'new_status' is required.")
            result = GovernanceBacklogTrackingService().update_backlog_status(
                backlog_id,
                new_status,
                note=self._optional_string(arguments, "note"),
            )
            status = "success" if result.status == "success" else "failed"
            persisted_items = backlog_store.list_backlog_items()
            sla_statuses = BacklogSlaCalculator().calculate(persisted_items)
            portfolio_summary = GovernancePortfolioAggregator().summarize(
                persisted_items,
                backlog_sla_statuses=sla_statuses,
            )
            trace = self._finish_trace(
                trace,
                status,
                result.message,
                operation="backlog_status_update",
                updated_backlog_id=backlog_id,
                old_status=result.old_status,
                new_status=result.new_status,
                overdue_count=portfolio_summary.overdue_count,
                blocked_count=portfolio_summary.blocked_count,
                owner_workload_summary=portfolio_summary.owner_workload,
            )
            return self._build_tool_response(
                tool_name,
                status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to update governance backlog status: {exc}",
                operation="backlog_status_update",
                updated_backlog_id=backlog_id or None,
                new_status=new_status or None,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to update governance backlog status.",
                None,
                trace,
            )

    def list_governance_backlog_items(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """List persisted governance backlog items with optional filters."""
        tool_name = "list_governance_backlog_items"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="backlog_list",
        )
        try:
            service = GovernanceBacklogTrackingService()
            items = backlog_store.list_backlog_items()
            sla_statuses = service.build_sla_statuses(items)
            items = service.filter_backlog_items(
                items,
                status=self._optional_string(arguments, "status"),
                priority=self._optional_string(arguments, "priority"),
                owner_role=self._optional_string(arguments, "owner_role"),
                gap_type=self._optional_string(arguments, "gap_type"),
                overdue_only=bool(arguments.get("overdue_only", False)),
                sla_status=self._optional_string(arguments, "sla_status"),
                backlog_sla_statuses=sla_statuses,
            )
            summary = service.summarize_backlog(items)
            filtered_ids = {item.backlog_id for item in items}
            filtered_sla_statuses = [
                status
                for status in sla_statuses
                if status.backlog_id in filtered_ids
            ]
            result_payload = {
                "governance_backlog_items": [item.model_dump() for item in items],
                "backlog_summary": summary.model_dump(),
                "backlog_sla_statuses": [
                    status.model_dump() for status in filtered_sla_statuses
                ],
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance backlog items were listed successfully.",
                operation="backlog_list",
                backlog_item_count=len(items),
                backlog_status_summary=summary.by_status,
                overdue_count=sum(1 for item in filtered_sla_statuses if item.is_overdue),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance backlog items were listed successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to list governance backlog items: {exc}",
                operation="backlog_list",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to list governance backlog items.",
                None,
                trace,
            )

    def _resolve_portfolio_inputs(
        self,
        arguments: dict[str, object],
    ) -> tuple[list[GovernanceBacklogItem], list[BacklogSlaStatus], WorkflowResult | None]:
        """Resolve backlog and SLA inputs for portfolio-level tools."""
        workflow_result = self._optional_workflow_result(arguments)
        file_path = self._optional_string(arguments, "file_path")
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

        items = self._coerce_governance_backlog_items(
            arguments.get("governance_backlog_items")
        )
        if workflow_result is not None and not items:
            if not workflow_result.governance_backlog_items:
                if not workflow_result.remediation_actions:
                    workflow_result = self._resolve_readiness_result_from_arguments(
                        {"workflow_result": workflow_result},
                        full_work_package=True,
                    )
                items, summary = GovernanceBacklogTrackingService().build_backlog_from_work_package(
                    workflow_result=workflow_result
                )
                workflow_result.governance_backlog_items = items
                workflow_result.backlog_summary = summary
            else:
                items = list(workflow_result.governance_backlog_items)
        if not items:
            items = backlog_store.list_backlog_items()

        sla_statuses = self._coerce_backlog_sla_statuses(
            arguments.get("backlog_sla_statuses")
        )
        if not sla_statuses:
            sla_statuses = BacklogSlaCalculator().calculate(items)
        if workflow_result is not None:
            workflow_result.governance_backlog_items = items
            workflow_result.backlog_sla_statuses = sla_statuses
        return items, sla_statuses, workflow_result

    def assess_governance_portfolio(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Assess backlog SLA status and governance portfolio summary."""
        tool_name = "assess_governance_portfolio"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="portfolio_assessment",
        )
        try:
            items, sla_statuses, workflow_result = self._resolve_portfolio_inputs(
                arguments
            )
            readiness_scores = (
                workflow_result.readiness_scores if workflow_result is not None else []
            )
            portfolio_summary = GovernancePortfolioAggregator().summarize(
                items,
                readiness_scores=readiness_scores,
                backlog_sla_statuses=sla_statuses,
            )
            progress_snapshot = ProgressSnapshotService().build_progress_snapshot(
                items,
                backlog_sla_statuses=sla_statuses,
                readiness_scores=readiness_scores,
                notes=self._optional_string(arguments, "notes"),
            )
            result_payload = {
                "governance_backlog_items": [item.model_dump() for item in items],
                "backlog_sla_statuses": [
                    status.model_dump() for status in sla_statuses
                ],
                "governance_portfolio_summary": portfolio_summary.model_dump(),
                "progress_snapshot": progress_snapshot.model_dump(),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance portfolio assessment was generated successfully.",
                stages_executed=[
                    "backlog_sla",
                    "portfolio_aggregation",
                    "progress_snapshot",
                ],
                operation="portfolio_assessment",
                backlog_item_count=len(items),
                overdue_count=portfolio_summary.overdue_count,
                blocked_count=portfolio_summary.blocked_count,
                owner_workload_summary=portfolio_summary.owner_workload,
                snapshot_id=progress_snapshot.snapshot_id,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance portfolio assessment was generated successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to assess governance portfolio: {exc}",
                operation="portfolio_assessment",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to assess governance portfolio.",
                None,
                trace,
            )

    def generate_progress_snapshot(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Generate and optionally save a local governance progress snapshot."""
        tool_name = "generate_progress_snapshot"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="progress_snapshot",
        )
        try:
            items, sla_statuses, workflow_result = self._resolve_portfolio_inputs(
                arguments
            )
            readiness_scores = (
                workflow_result.readiness_scores if workflow_result is not None else []
            )
            service = ProgressSnapshotService()
            snapshot = service.build_progress_snapshot(
                items,
                backlog_sla_statuses=sla_statuses,
                readiness_scores=readiness_scores,
                notes=self._optional_string(arguments, "notes"),
            )
            saved = (
                service.save_progress_snapshot(snapshot)
                if bool(arguments.get("save", False))
                else None
            )
            result_payload = {
                "progress_snapshot": snapshot.model_dump(),
                "saved": saved,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance progress snapshot was generated successfully.",
                operation="progress_snapshot",
                backlog_item_count=len(items),
                overdue_count=snapshot.overdue_count,
                blocked_count=snapshot.blocked_count,
                snapshot_id=snapshot.snapshot_id,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance progress snapshot was generated successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to generate governance progress snapshot: {exc}",
                operation="progress_snapshot",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to generate governance progress snapshot.",
                None,
                trace,
            )

    def list_governance_progress_snapshots(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """List saved local governance progress snapshots."""
        tool_name = "list_governance_progress_snapshots"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="progress_snapshot_list",
        )
        try:
            snapshots = ProgressSnapshotService().list_progress_snapshots()
            result_payload = {
                "progress_snapshots": [
                    snapshot.model_dump() for snapshot in snapshots
                ],
                "snapshot_count": len(snapshots),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance progress snapshots were listed successfully.",
                operation="progress_snapshot_list",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance progress snapshots were listed successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to list governance progress snapshots: {exc}",
                operation="progress_snapshot_list",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to list governance progress snapshots.",
                None,
                trace,
            )

# TODO: add MCP and OpenAI tool-calling adapters once the local tool contract and trace schema remain stable.
