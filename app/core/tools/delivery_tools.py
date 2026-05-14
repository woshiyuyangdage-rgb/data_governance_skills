"""Delivery, reporting, batch, and confirmation workbook tool handlers."""

from pathlib import Path

from app.core.delivery.confirmation_workbook_importer import (
    ConfirmationWorkbookImporter,
)
from app.core.delivery.delivery_service import DeliveryService
from app.core.governance.batch_snapshot_store import (
    list_batch_snapshots,
    load_latest_batch_snapshot,
)
from app.core.governance.incremental_diff_service import IncrementalDiffService
from app.core.models.tool_call_response import ToolCallResponse
from app.core.orchestrator.pipeline_service import (
    run_batch_governance_workflow_from_files,
    run_full_governance_backlog_package_from_file,
    run_governance_backlog_build_from_file,
)
from app.core.reports.report_service import (
    DEFAULT_REPORT_OUTPUT_DIR,
    build_report_base_filename,
    export_all_reports,
)


class DeliveryToolMixin:
    """Tool handlers for governance delivery assets and batch rerun flows."""

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
            workflow_result = self._optional_workflow_result(arguments)
            file_path = self._optional_string(arguments, "file_path")
            apply_review = bool(arguments.get("apply_review_replay", True))
            if workflow_result is None:
                if not file_path:
                    raise ValueError(
                        "Argument 'workflow_result' or 'file_path' is required."
                    )
                workflow_result = (
                    run_full_governance_backlog_package_from_file(file_path)
                    if apply_review
                    else run_governance_backlog_build_from_file(file_path)
                )
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
            workflow_result = self._optional_workflow_result(arguments)
            file_path = self._optional_string(arguments, "file_path")
            apply_review = bool(arguments.get("apply_review_replay", True))
            if workflow_result is None:
                if not file_path:
                    raise ValueError(
                        "Argument 'workflow_result' or 'file_path' is required."
                    )
                workflow_result = (
                    run_full_governance_backlog_package_from_file(file_path)
                    if apply_review
                    else run_governance_backlog_build_from_file(file_path)
                )
            workflow_result = DeliveryService().build_governance_delivery_package(
                workflow_result,
                output_dir=self._optional_string(arguments, "output_dir"),
                base_name=self._optional_string(arguments, "base_filename")
                or self._optional_string(arguments, "base_name"),
            )

            package_result = workflow_result.governance_delivery_package_result
            manifest = workflow_result.governance_delivery_manifest
            generated_files = (
                dict(package_result.generated_files) if package_result is not None else {}
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

    def _batch_arguments(
        self,
        arguments: dict[str, object],
    ) -> tuple[list[str], str, str | None]:
        file_paths = (
            [
                str(path)
                for path in arguments.get("file_paths", [])
                if str(path).strip()
            ]
            if isinstance(arguments.get("file_paths"), list)
            else []
        )
        file_path = self._optional_string(arguments, "file_path")
        if file_path:
            file_paths.append(file_path)
        if not file_paths:
            raise ValueError("Argument 'file_paths' or 'file_path' is required.")
        group_by = self._optional_string(arguments, "group_by") or "system_name"
        batch_name = self._optional_string(
            arguments,
            "batch_name",
        ) or self._optional_string(
            arguments,
            "base_filename",
        )
        return file_paths, group_by, batch_name

    def run_batch_governance(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run multi-file batch governance."""
        tool_name = "run_batch_governance"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_paths, group_by, batch_name = self._batch_arguments(arguments)
            result = run_batch_governance_workflow_from_files(
                file_paths,
                group_by=group_by,
                changed_only=False,
                batch_name=batch_name,
            )
            summary = result.incremental_diff_summary
            rerun_scope = result.rerun_scope_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                batch_name=rerun_scope.get("batch_name") if rerun_scope else batch_name,
                file_count=len(file_paths),
                group_count=len(result.batch_group_results),
                changed_count=summary.changed_count if summary else None,
                new_count=summary.new_count if summary else None,
                unchanged_count=summary.unchanged_count if summary else None,
                removed_count=summary.removed_count if summary else None,
                rerun_object_count=(
                    rerun_scope.get("rerun_object_count") if rerun_scope else None
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
                f"Failed to run batch governance: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run batch governance.",
                None,
                trace,
            )

    def run_incremental_rerun(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run changed-only batch governance using local snapshots."""
        tool_name = "run_incremental_rerun"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_paths, group_by, batch_name = self._batch_arguments(arguments)
            result = run_batch_governance_workflow_from_files(
                file_paths,
                group_by=group_by,
                changed_only=True,
                batch_name=batch_name,
            )
            summary = result.incremental_diff_summary
            rerun_scope = result.rerun_scope_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                batch_name=rerun_scope.get("batch_name") if rerun_scope else batch_name,
                file_count=len(file_paths),
                group_count=len(result.batch_group_results),
                changed_count=summary.changed_count if summary else None,
                new_count=summary.new_count if summary else None,
                unchanged_count=summary.unchanged_count if summary else None,
                removed_count=summary.removed_count if summary else None,
                rerun_object_count=(
                    rerun_scope.get("rerun_object_count") if rerun_scope else None
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
                f"Failed to run incremental rerun: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run incremental rerun.",
                None,
                trace,
            )

    def compare_governance_snapshots(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Compare the latest stored snapshot with itself or return latest snapshot metadata."""
        tool_name = "compare_governance_snapshots"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            batch_name = (
                self._optional_string(arguments, "batch_name")
                or "default_batch_governance"
            )
            latest = load_latest_batch_snapshot(batch_name)
            snapshots = list_batch_snapshots(batch_name)
            fingerprints = latest.get("fingerprints", []) if latest else []
            diff_items = IncrementalDiffService().compare_fingerprints(
                fingerprints,
                fingerprints,
            )
            summary = IncrementalDiffService.build_incremental_diff_summary(diff_items)
            latest_payload = None
            if latest:
                latest_payload = dict(latest)
                latest_payload["fingerprints"] = [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in fingerprints
                ]
            result = {
                "batch_name": batch_name,
                "latest_snapshot": latest_payload,
                "snapshots": snapshots,
                "incremental_diff_items": [
                    item.model_dump() for item in diff_items
                ],
                "incremental_diff_summary": summary.model_dump(),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance snapshots were compared successfully.",
                batch_name=batch_name,
                changed_count=summary.changed_count,
                new_count=summary.new_count,
                unchanged_count=summary.unchanged_count,
                removed_count=summary.removed_count,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance snapshots were compared successfully.",
                result,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to compare governance snapshots: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to compare governance snapshots.",
                None,
                trace,
            )

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
