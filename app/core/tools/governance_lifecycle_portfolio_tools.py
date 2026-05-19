"""Portfolio and progress snapshot tool handlers for the governance executor."""

from app.core.governance import (
    GovernancePortfolioAggregator,
    ProgressSnapshotService,
)
from app.core.models.tool_call_response import ToolCallResponse
from app.core.tools.governance_lifecycle_helpers import (
    resolve_portfolio_inputs,
)


class GovernancePortfolioToolMixin:
    """Tool handlers for portfolio summaries and progress snapshots."""

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
            items, sla_statuses, workflow_result = resolve_portfolio_inputs(
                self,
                arguments,
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
                "governance_backlog_items": [
                    item.model_dump() for item in items
                ],
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
            items, sla_statuses, workflow_result = resolve_portfolio_inputs(
                self,
                arguments,
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
