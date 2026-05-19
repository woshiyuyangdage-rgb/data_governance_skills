"""Governance delivery package and confirmation workbook export handlers."""

from typing import Protocol

from app.core.delivery.delivery_service import DeliveryService
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_backlog_package_from_file,
    run_governance_backlog_build_from_file,
)


class DeliveryPackageToolContext(Protocol):
    """Subset of executor helpers used by delivery package resolution."""

    def _optional_string(
        self, arguments: dict[str, object], name: str
    ) -> str | None: ...

    def _optional_workflow_result(
        self, arguments: dict[str, object]
    ) -> WorkflowResult | None: ...


def _resolve_delivery_workflow_result(
    context: DeliveryPackageToolContext,
    arguments: dict[str, object],
) -> WorkflowResult:
    """Resolve a workflow result from direct payload or local input file."""
    workflow_result = context._optional_workflow_result(arguments)
    file_path = context._optional_string(arguments, "file_path")
    apply_review = bool(arguments.get("apply_review_replay", True))
    if workflow_result is not None:
        return workflow_result
    if not file_path:
        raise ValueError("Argument 'workflow_result' or 'file_path' is required.")
    return (
        run_full_governance_backlog_package_from_file(file_path)
        if apply_review
        else run_governance_backlog_build_from_file(file_path)
    )


class DeliveryPackageToolMixin:
    """Tool handlers for confirmation workbook and delivery package exports."""

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
            workflow_result = _resolve_delivery_workflow_result(self, arguments)
            output_dir = self._optional_string(arguments, "output_dir")
            base_name = self._optional_string(
                arguments,
                "base_filename",
            ) or self._optional_string(
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
            workflow_result = _resolve_delivery_workflow_result(self, arguments)
            workflow_result = DeliveryService().build_governance_delivery_package(
                workflow_result,
                output_dir=self._optional_string(arguments, "output_dir"),
                base_name=self._optional_string(arguments, "base_filename")
                or self._optional_string(arguments, "base_name"),
            )

            package_result = workflow_result.governance_delivery_package_result
            manifest = workflow_result.governance_delivery_manifest
            generated_files = (
                dict(package_result.generated_files)
                if package_result is not None
                else {}
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
