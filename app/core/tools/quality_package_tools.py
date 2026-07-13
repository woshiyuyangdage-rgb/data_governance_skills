"""Quality package tool handlers for the governance executor."""

from pathlib import Path
from typing import Protocol

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.execution_package_export_result import (
    ExecutionPackageExportResult,
)
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
)
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.review.quality_review_service import build_confirmed_quality_rules
from app.core.tools.quality_tool_payloads import (
    coerce_confirmed_quality_rules,
    coerce_execution_ready_package,
)
from app.core.utils.file_utils import resolve_allowed_local_path
from app.core.utils.time_utils import utc_now_compact


class QualityPackageToolContext(Protocol):
    """Subset of executor helpers used by quality package resolution functions."""

    def _optional_string(
        self, arguments: dict[str, object], name: str
    ) -> str | None: ...

    def _optional_workflow_result(
        self, arguments: dict[str, object]
    ) -> WorkflowResult | None: ...


def _resolve_execution_ready_package_from_arguments(
    context: QualityPackageToolContext,
    arguments: dict[str, object],
) -> tuple[ExecutionReadyPackage, WorkflowResult | None, list[ConfirmedQualityRule]]:
    """Resolve or build an execution-ready package from tool arguments."""
    package = coerce_execution_ready_package(
        arguments.get("execution_ready_package", arguments.get("package"))
    )
    workflow_result = context._optional_workflow_result(arguments)
    confirmed_rules = coerce_confirmed_quality_rules(
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

    file_path = context._optional_string(arguments, "file_path")
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
            "An execution_ready_package, confirmed_quality_rules, workflow_result,"
            " or file_path is required."
        )

    profile_name = (
        context._optional_string(arguments, "profile_name")
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


class QualityPackageToolMixin:
    """Tool handlers for quality rule export and execution package flows."""

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
            confirmed_rules = coerce_confirmed_quality_rules(
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

            output_dir = resolve_allowed_local_path(
                self._optional_string(arguments, "output_dir")
                or (Path(__file__).resolve().parents[3] / "outputs" / "rule_exports"),
                path_label="output_dir",
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
                    "export_format must be one of json, custom_json, dbt, dbt_yaml,"
                    " yaml, or both."
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
                _resolve_execution_ready_package_from_arguments(self, arguments)
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
            package, _, confirmed_rules = (
                _resolve_execution_ready_package_from_arguments(self, arguments)
            )
            output_dir = resolve_allowed_local_path(
                self._optional_string(arguments, "output_dir")
                or (
                    Path(__file__).resolve().parents[3]
                    / "outputs"
                    / "execution_packages"
                ),
                path_label="output_dir",
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
                    "export_format must be one of json, package_json, manifest,"
                    " package_manifest, dbt, dbt_yaml, yaml, all, or both."
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
