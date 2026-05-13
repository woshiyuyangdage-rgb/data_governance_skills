"""Tests for round-trip rerun scope service."""

from app.core.governance.roundtrip_rerun_service import RoundTripRerunService
from app.core.models.confirmation_roundtrip_result import ConfirmationRoundTripResult
from app.core.models.workbook_import_summary import WorkbookImportSummary


def test_roundtrip_rerun_scope_and_summary() -> None:
    import_summary = WorkbookImportSummary(
        workbook_type="mapping_confirmation",
        total_rows=1,
        imported_count=1,
        skipped_count=0,
        invalid_count=0,
        accepted_count=1,
        rejected_count=0,
        edited_count=0,
        manual_review_count=0,
    )
    result = ConfirmationRoundTripResult(
        workbook_type="mapping_confirmation",
        import_summary=import_summary,
        changed_object_keys=["customer.customer_id"],
        status="success",
    )
    service = RoundTripRerunService()

    scope = service.build_rerun_scope_from_roundtrip([result])
    summary = service.summarize_roundtrip_changed_objects([result])

    assert scope["rerun_changed_only"] is True
    assert scope["changed_object_count"] == 1
    assert summary["by_workbook_type"]["mapping_confirmation"] == 1

