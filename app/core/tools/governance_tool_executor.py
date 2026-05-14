"""Standard local executor for governance tool contracts."""

from app.core.agent.agent_shell_service import AgentShellService
from app.core.agent.session_store import append_trace_to_session
from app.core.audit.trace_store import build_trace_summary, save_trace
from app.core.control_plane.control_plane_service import ControlPlaneService
from app.core.intent.intent_task_service import interpret_and_run_task
from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.execution_trace import ExecutionTrace
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.task_service import run_governance_task
from app.core.tools.agent_tools import AgentToolMixin
from app.core.tools.control_plane_tools import ControlPlaneToolMixin
from app.core.tools.delivery_tools import DeliveryToolMixin
from app.core.tools.dispatch_tools import ToolDispatchMixin
from app.core.tools.governance_lifecycle_tools import GovernanceLifecycleToolMixin
from app.core.tools.quality_tools import QualityToolMixin
from app.core.tools.template_intake_tools import TemplateIntakeToolMixin
from app.core.utils.time_utils import utc_now_seconds


class GovernanceToolExecutor(
    ToolDispatchMixin,
    AgentToolMixin,
    DeliveryToolMixin,
    QualityToolMixin,
    TemplateIntakeToolMixin,
    GovernanceLifecycleToolMixin,
    ControlPlaneToolMixin,
):
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
