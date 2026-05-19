"""Confirmation workbook import and template tool handlers."""

from app.core.delivery.confirmation_workbook_importer import (
    ConfirmationWorkbookImporter,
)
from app.core.models.tool_call_response import ToolCallResponse


class DeliveryConfirmationToolMixin:
    """Tool handlers for confirmation workbook import flows."""

    def import_confirmation_workbook(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Import and merge one filled confirmation workbook."""
        tool_name = "import_confirmation_workbook"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            workbook_type = (
                self._optional_string(arguments, "workbook_type")
                or "mapping_confirmation"
            )
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            result = WorkflowEngine().import_confirmation_workbook_and_merge(
                file_path,
                workbook_type,
            )
            summary = (
                result.workbook_import_summaries[0]
                if result.workbook_import_summaries
                else None
            )
            changed_summary = result.roundtrip_changed_objects_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                workbook_type=workbook_type,
                imported_count=summary.imported_count if summary else None,
                invalid_count=summary.invalid_count if summary else None,
                changed_object_count=int(
                    changed_summary.get("changed_object_count", 0) or 0
                ),
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to import confirmation workbook: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to import confirmation workbook.",
                None,
                trace,
            )

    def import_confirmation_and_rerun(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Import confirmation workbook and prepare changed-object rerun scope."""
        tool_name = "import_confirmation_and_rerun"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            workbook_type = (
                self._optional_string(arguments, "workbook_type")
                or "mapping_confirmation"
            )
            rerun_changed_only = bool(arguments.get("rerun_changed_only", True))
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            result = WorkflowEngine().import_confirmation_workbook_and_rerun(
                file_path,
                workbook_type,
                rerun_changed_only=rerun_changed_only,
            )
            summary = (
                result.workbook_import_summaries[0]
                if result.workbook_import_summaries
                else None
            )
            changed_summary = result.roundtrip_changed_objects_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                workbook_type=workbook_type,
                imported_count=summary.imported_count if summary else None,
                invalid_count=summary.invalid_count if summary else None,
                changed_object_count=int(
                    changed_summary.get("changed_object_count", 0) or 0
                ),
                rerun_changed_only=rerun_changed_only,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to import confirmation workbook and rerun: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to import confirmation workbook and rerun.",
                None,
                trace,
            )

    def diagnose_confirmation_template(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Diagnose a confirmation workbook template."""
        tool_name = "diagnose_confirmation_template"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            result = ConfirmationWorkbookImporter().diagnose_confirmation_template(
                file_path,
                workbook_type=self._optional_string(arguments, "workbook_type"),
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            trace = self._finish_trace(
                trace,
                "success",
                result.message or "Confirmation template diagnosed.",
                workbook_type=result.workbook_type,
                confirmation_template_name=result.matched_template_name,
                template_match_confidence=result.confidence,
                matched_sheet_name=result.matched_sheet_name,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                trace.message or "Diagnosed.",
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def import_confirmation_with_template(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Import and merge confirmation workbook using a template profile."""
        tool_name = "import_confirmation_with_template"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            rerun_changed_only = bool(arguments.get("rerun_changed_only", False))
            if rerun_changed_only:
                result = WorkflowEngine().import_confirmation_with_template_and_rerun(
                    file_path,
                    template_name=self._optional_string(
                        arguments,
                        "confirmation_template_name",
                    ),
                    workbook_type=self._optional_string(arguments, "workbook_type"),
                    sheet_name=self._optional_string(arguments, "sheet_name"),
                    rerun_changed_only=True,
                )
            else:
                result = WorkflowEngine().import_confirmation_with_template(
                    file_path,
                    template_name=self._optional_string(
                        arguments,
                        "confirmation_template_name",
                    ),
                    workbook_type=self._optional_string(arguments, "workbook_type"),
                    sheet_name=self._optional_string(arguments, "sheet_name"),
                )
            summary = (
                result.workbook_import_summaries[0]
                if result.workbook_import_summaries
                else None
            )
            match = result.confirmation_template_match_result
            mapping = result.confirmation_template_mapping_result
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                workbook_type=summary.workbook_type if summary else None,
                confirmation_template_name=(
                    mapping.template_name
                    if mapping
                    else (match.matched_template_name if match else None)
                ),
                template_match_confidence=match.confidence if match else None,
                matched_sheet_name=match.matched_sheet_name if match else None,
                imported_count=summary.imported_count if summary else None,
                invalid_count=summary.invalid_count if summary else None,
                rerun_changed_only=rerun_changed_only,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)
