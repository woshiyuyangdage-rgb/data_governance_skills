"""Governance report export tool handlers."""

from pathlib import Path

from app.core.models.tool_call_response import ToolCallResponse
from app.core.reports.report_service import (
    DEFAULT_REPORT_OUTPUT_DIR,
    build_report_base_filename,
    export_all_reports,
)


class DeliveryReportToolMixin:
    """Tool handlers for governance report exports."""

    def export_governance_reports(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Export governance reports from an existing workflow result."""
        tool_name = "export_governance_reports"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=self._optional_string(arguments, "profile_name"),
        )
        try:
            workflow_result = self._coerce_workflow_result(arguments)
            profile_name = self._resolve_export_profile_name(arguments, workflow_result)
            output_dir = self._optional_string(arguments, "output_dir") or str(
                DEFAULT_REPORT_OUTPUT_DIR
            )
            base_filename = self._optional_string(
                arguments,
                "base_filename",
            ) or build_report_base_filename(profile_name=profile_name)

            exported_files = export_all_reports(
                workflow_result,
                output_dir=output_dir,
                base_filename=base_filename,
            )
            trace.profile_name = profile_name
            trace = self._finish_trace(
                trace,
                "success",
                "Governance reports were exported successfully.",
                exported_files=exported_files,
                review_summary=(
                    workflow_result.review_summary.model_dump()
                    if workflow_result.review_summary is not None
                    else {}
                ),
                notes=[
                    f"Reports exported to {Path(output_dir).resolve()}",
                ],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance reports were exported successfully.",
                {
                    "profile_name": profile_name,
                    "output_dir": output_dir,
                    "base_filename": base_filename,
                    "exported_files": exported_files,
                },
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to export governance reports: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to export governance reports.",
                None,
                trace,
            )
