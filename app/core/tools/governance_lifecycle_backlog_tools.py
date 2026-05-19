"""Backlog tool handlers for the governance lifecycle executor."""

import app.core.governance.backlog_store as backlog_store
from app.core.governance import (
    BacklogSlaCalculator,
    GovernanceBacklogTrackingService,
    GovernancePortfolioAggregator,
)
from app.core.models.tool_call_response import ToolCallResponse
from app.core.tools.governance_lifecycle_helpers import (
    resolve_backlog_items_from_arguments,
)


class GovernanceBacklogToolMixin:
    """Tool handlers for backlog build, status updates, and listing."""

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
            items, workflow_result = resolve_backlog_items_from_arguments(
                self,
                arguments,
            )
            summary = service.summarize_backlog(items)
            persisted = None
            if bool(arguments.get("persist", False)):
                persisted = service.persist_backlog_items(
                    items,
                    append=bool(arguments.get("append", True)),
                )
            result_payload = {
                "governance_backlog_items": [
                    item.model_dump() for item in items
                ],
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
                "governance_backlog_items": [
                    item.model_dump() for item in items
                ],
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
                overdue_count=sum(
                    1 for item in filtered_sla_statuses if item.is_overdue
                ),
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
