"""Quality recommendation tool handlers for the governance executor."""

from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.tool_call_response import ToolCallResponse
from app.core.orchestrator.task_service import run_governance_task


class QualityRecommendationToolMixin:
    """Tool handlers for quality recommendation flows."""

    def recommend_quality_rules(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run the workflow chain up to quality rule recommendation."""
        tool_name = "recommend_quality_rules"
        apply_review_replay = bool(arguments.get("apply_review_replay", False))
        default_profile = (
            "diagnosis_mapping_stg_quality_with_review"
            if apply_review_replay
            else "diagnosis_mapping_stg_quality"
        )
        profile_name = (
            self._optional_string(arguments, "profile_name") or default_profile
        )
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
            low_confidence_count = int(
                review_queue.get("low_confidence_rule_count", 0) or 0
            )
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
