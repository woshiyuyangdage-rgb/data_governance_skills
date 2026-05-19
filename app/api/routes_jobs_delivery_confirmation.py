"""Confirmation workbook validation and round-trip job routes."""

from fastapi import APIRouter

from app.api.job_requests import ConfirmationWorkbookImportRequest
from app.api.tool_response import call_tool_and_wrap

router = APIRouter()


@router.post("/validate-confirmation-workbook")
def validate_confirmation_workbook_route(
    payload: ConfirmationWorkbookImportRequest,
) -> dict[str, object]:
    """Validate one confirmation workbook before import."""
    from app.core.delivery.confirmation_workbook_importer import (
        ConfirmationWorkbookImporter,
    )

    result = ConfirmationWorkbookImporter().validate_workbook(
        payload.file_path,
        payload.workbook_type,
    )
    return {"validation_result": result.model_dump()}


@router.post("/import-confirmation-workbook")
def import_confirmation_workbook_route(
    payload: ConfirmationWorkbookImportRequest,
) -> dict[str, object]:
    """Import one filled confirmation workbook and merge local updates."""
    return call_tool_and_wrap(
        "import_confirmation_workbook",
        payload.model_dump(exclude_none=True),
        success_statuses={"success", "partial_success"},
    )


@router.post("/import-confirmation-and-rerun")
def import_confirmation_and_rerun_route(
    payload: ConfirmationWorkbookImportRequest,
) -> dict[str, object]:
    """Import one confirmation workbook and prepare changed-object rerun scope."""
    return call_tool_and_wrap(
        "import_confirmation_and_rerun",
        payload.model_dump(exclude_none=True),
        success_statuses={"success", "partial_success"},
    )


@router.get("/roundtrip-changed-objects-summary")
def roundtrip_changed_objects_summary_route() -> dict[str, object]:
    """Return a lightweight description of round-trip changed object output."""
    return {
        "message": "Round-trip changed objects are returned by import-confirmation-workbook and import-confirmation-and-rerun.",
        "summary_fields": [
            "changed_object_count",
            "changed_object_keys",
            "by_workbook_type",
        ],
    }
