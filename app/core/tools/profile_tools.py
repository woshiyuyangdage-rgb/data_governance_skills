"""Direct governance profile execution tool handler."""

from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.tool_call_response import ToolCallResponse
from app.core.orchestrator.task_service import run_governance_task


class ProfileToolMixin:
    """Tool handler for direct workflow profile execution."""

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
