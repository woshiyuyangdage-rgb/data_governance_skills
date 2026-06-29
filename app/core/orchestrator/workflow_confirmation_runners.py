"""Confirmation workbook workflow runner helpers."""

from app.core.delivery.confirmation_roundtrip_service import (
    ConfirmationRoundTripService,
)
from app.core.delivery.confirmation_workbook_importer import (
    ConfirmationWorkbookImporter,
)
from app.core.governance.roundtrip_rerun_service import RoundTripRerunService
from app.core.models.workflow_result import WorkflowResult


class WorkflowConfirmationRunnerMixin:
    """Run confirmation workbook import and round-trip workflows."""

    def import_confirmation_workbook_and_merge(
        self,
        file_path: str,
        workbook_type: str,
    ) -> WorkflowResult:
        """Validate, import, and merge one confirmation workbook."""
        importer = ConfirmationWorkbookImporter()
        payload = importer.import_workbook(file_path, workbook_type)
        roundtrip_result = ConfirmationRoundTripService().apply_roundtrip_updates(payload)
        changed_summary = RoundTripRerunService().summarize_roundtrip_changed_objects(
            [roundtrip_result]
        )
        return WorkflowResult(
            status=roundtrip_result.status,
            message=roundtrip_result.message or "",
            workbook_import_summaries=[payload.import_summary],
            roundtrip_results=[roundtrip_result],
            roundtrip_changed_objects_summary=changed_summary,
            skill_outputs={
                "workbook_import_output": {
                    "validation_result": payload.validation_result.model_dump(),
                    "row_results": [row.model_dump() for row in payload.row_results],
                    "normalized_row_count": len(payload.normalized_rows),
                },
                "roundtrip_merge_output": roundtrip_result.model_dump(),
            },
        )

    def import_confirmation_workbook_and_rerun(
        self,
        file_path: str,
        workbook_type: str,
        rerun_changed_only: bool = True,
    ) -> WorkflowResult:
        """Import confirmation workbook and prepare changed-only rerun scope."""
        result = self.import_confirmation_workbook_and_merge(file_path, workbook_type)
        scope = RoundTripRerunService().build_rerun_scope_from_roundtrip(
            result.roundtrip_results
        )
        scope["rerun_changed_only"] = rerun_changed_only
        result.rerun_scope_summary = scope
        if result.status in {"success", "partial_success"}:
            result.message = (
                f"{result.message} Changed-object rerun scope was prepared."
            )
        result.skill_outputs["roundtrip_rerun_scope_output"] = scope
        return result

    def diagnose_confirmation_template(
        self,
        file_path: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkflowResult:
        """Diagnose a confirmation workbook template before import."""
        match_result = ConfirmationWorkbookImporter().diagnose_confirmation_template(
            file_path,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        return WorkflowResult(
            status="success" if not match_result.fallback_used else "failed",
            message=match_result.message or "",
            confirmation_template_match_result=match_result,
            skill_outputs={
                "confirmation_template_diagnosis_output": match_result.model_dump()
            },
        )

    def import_confirmation_with_template(
        self,
        file_path: str,
        template_name: str | None = None,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkflowResult:
        """Import and merge a confirmation workbook using a template profile."""
        importer = ConfirmationWorkbookImporter()
        payload = importer.import_confirmation_with_template(
            file_path,
            template_name=template_name,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        roundtrip_result = ConfirmationRoundTripService().apply_roundtrip_updates(payload)
        changed_summary = RoundTripRerunService().summarize_roundtrip_changed_objects(
            [roundtrip_result]
        )
        return WorkflowResult(
            status=roundtrip_result.status,
            message=roundtrip_result.message or "",
            workbook_import_summaries=[payload.import_summary],
            roundtrip_results=[roundtrip_result],
            roundtrip_changed_objects_summary=changed_summary,
            confirmation_template_match_result=payload.confirmation_template_match_result,
            confirmation_template_mapping_result=payload.confirmation_template_mapping_result,
            skill_outputs={
                "confirmation_template_import_output": {
                    "validation_result": payload.validation_result.model_dump(),
                    "template_match_result": (
                        payload.confirmation_template_match_result.model_dump()
                        if payload.confirmation_template_match_result
                        else None
                    ),
                    "template_mapping_result": (
                        payload.confirmation_template_mapping_result.model_dump()
                        if payload.confirmation_template_mapping_result
                        else None
                    ),
                    "row_results": [row.model_dump() for row in payload.row_results],
                    "normalized_row_count": len(payload.normalized_rows),
                },
                "roundtrip_merge_output": roundtrip_result.model_dump(),
            },
        )

    def import_confirmation_with_template_and_rerun(
        self,
        file_path: str,
        template_name: str | None = None,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
        rerun_changed_only: bool = True,
    ) -> WorkflowResult:
        """Template-aware import plus changed-object rerun scope preparation."""
        result = self.import_confirmation_with_template(
            file_path,
            template_name=template_name,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        scope = RoundTripRerunService().build_rerun_scope_from_roundtrip(
            result.roundtrip_results
        )
        scope["rerun_changed_only"] = rerun_changed_only
        result.rerun_scope_summary = scope
        if result.status in {"success", "partial_success"}:
            result.message = (
                f"{result.message} Changed-object rerun scope was prepared."
            )
        result.skill_outputs["roundtrip_rerun_scope_output"] = scope
        return result
