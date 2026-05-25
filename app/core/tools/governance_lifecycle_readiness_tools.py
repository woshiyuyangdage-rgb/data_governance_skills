"""Readiness and governance work package tool handlers."""

from app.core.models.tool_call_response import ToolCallResponse
from app.core.tools.governance_lifecycle_helpers import (
    maybe_export_governance_work_package,
    resolve_readiness_result_from_arguments,
)


class GovernanceReadinessToolMixin:
    """Tool handlers for governance readiness and work package flows."""

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
            workflow_result = resolve_readiness_result_from_arguments(
                self,
                arguments,
                full_work_package=False,
            )
            result_payload = {
                "readiness_scores": [
                    score.model_dump() for score in workflow_result.readiness_scores
                ],
                "ai_ready_scores": [
                    score.model_dump() for score in workflow_result.ai_ready_scores
                ],
                "governance_gaps": [
                    gap.model_dump() for gap in workflow_result.governance_gaps
                ],
                "readiness_summary": dict(workflow_result.readiness_summary or {}),
                "ai_ready_summary": dict(workflow_result.ai_ready_summary or {}),
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
            workflow_result = resolve_readiness_result_from_arguments(
                self,
                arguments,
                full_work_package=True,
            )
            exported_files = maybe_export_governance_work_package(
                self,
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
                "ai_ready_scores": [
                    score.model_dump() for score in workflow_result.ai_ready_scores
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
                "ai_ready_summary": dict(workflow_result.ai_ready_summary or {}),
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
