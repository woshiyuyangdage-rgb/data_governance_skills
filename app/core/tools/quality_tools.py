"""Quality rule and execution package tool handlers for the governance executor."""

from pathlib import Path

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_package_export_result import (
    ExecutionPackageExportResult,
)
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
)
from app.core.orchestrator.task_service import run_governance_task
from app.core.review.quality_batch_review_service import (
    bulk_accept_by_rule_type,
    bulk_accept_by_table,
    bulk_mark_manual_review_by_low_confidence,
    summarize_review_queue,
)
from app.core.review.quality_override_store import (
    load_quality_rule_overrides,
    save_quality_rule_review_records,
)
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.tools.quality_tool_payloads import (
    coerce_confirmed_quality_rules,
    coerce_cross_field_quality_rules,
    coerce_execution_ready_package,
    coerce_quality_review_records,
    coerce_quality_rule_suggestions,
    cross_field_rules_as_suggestions,
)
from app.core.utils.time_utils import utc_now_compact


class QualityToolMixin:
    """Tool handlers for quality rule review and execution package flows."""

    @staticmethod
    def _coerce_quality_rule_suggestions(
        payload: object,
    ) -> list[QualityRuleSuggestion]:
        return coerce_quality_rule_suggestions(payload)

    @staticmethod
    def _coerce_cross_field_quality_rules(
        payload: object,
    ) -> list[CrossFieldQualityRule]:
        return coerce_cross_field_quality_rules(payload)

    @staticmethod
    def _cross_field_rules_as_suggestions(
        rules: list[CrossFieldQualityRule],
    ) -> list[QualityRuleSuggestion]:
        return cross_field_rules_as_suggestions(rules)

    @staticmethod
    def _coerce_quality_review_records(
        payload: object,
    ) -> list[QualityRuleReviewRecord]:
        return coerce_quality_review_records(payload)

    @staticmethod
    def _coerce_confirmed_quality_rules(
        payload: object,
    ) -> list[ConfirmedQualityRule]:
        return coerce_confirmed_quality_rules(payload)

    @staticmethod
    def _coerce_execution_ready_package(payload: object) -> ExecutionReadyPackage | None:
        return coerce_execution_ready_package(payload)

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

            reviewed_suggestions, applied_count, _ = (
                apply_quality_rule_overrides_to_results(
                    suggestions,
                    records,
                )
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
                field_rule_count=sum(
                    1 for rule in suggestions if rule.rule_scope == "field"
                ),
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
                cross_field_rule_count=int(
                    summary.get("cross_field_rule_count", 0) or 0
                ),
                low_confidence_rule_count=int(
                    summary.get("low_confidence_rule_count", 0) or 0
                ),
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
                    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
                        file_path
                    )
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
                or f"confirmed_quality_rules_{utc_now_compact()}"
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

        if (
            workflow_result is not None
            and workflow_result.execution_ready_package is not None
        ):
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
                or f"execution_ready_package_{utc_now_compact()}"
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
