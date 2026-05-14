"""Readiness, backlog, portfolio, and progress snapshot tool handlers."""

import json
from pathlib import Path

import app.core.governance.backlog_store as backlog_store
from app.core.governance import (
    BacklogSlaCalculator,
    GapClassifier,
    GovernanceBacklogTrackingService,
    GovernancePortfolioAggregator,
    ProgressSnapshotService,
    ReadinessAssessor,
    RemediationPlanner,
)
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.remediation_action import RemediationAction
from app.core.models.tool_call_response import ToolCallResponse
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


class GovernanceLifecycleToolMixin:
    """Tool handlers for governance readiness, backlog, and portfolio flows."""

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
                return run_governance_readiness_assessment_with_review_from_file(
                    file_path
                )
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
            or (
                Path(__file__).resolve().parents[3]
                / "outputs"
                / "governance_work_packages"
            )
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        base_filename = (
            self._optional_string(arguments, "base_filename")
            or f"governance_work_package_{utc_now_compact()}"
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
