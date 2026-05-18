"""Readiness, delivery, batch, and confirmation round-trip job routes."""

from fastapi import APIRouter

from app.api.job_requests import (
    BatchGovernanceRequest,
    BatchSnapshotCompareRequest,
    ConfirmationWorkbookImportRequest,
    GovernanceDeliveryPackageRequest,
    GovernanceReadinessAssessmentRequest,
    GovernanceWorkPackageBuildRequest,
)
from app.api.tool_response import call_tool_and_expand, call_tool_and_wrap
from app.core.governance.batch_snapshot_store import list_batch_snapshots

router = APIRouter()


@router.post("/assess-governance-readiness")
def assess_governance_readiness_route(
    payload: GovernanceReadinessAssessmentRequest,
) -> dict[str, object]:
    """Assess governance readiness scores and classify gaps."""
    return call_tool_and_expand(
        "assess_governance_readiness",
        payload.model_dump(exclude_none=True),
    )


@router.post("/build-governance-work-package")
def build_governance_work_package_route(
    payload: GovernanceWorkPackageBuildRequest,
) -> dict[str, object]:
    """Build remediation actions and a governance work package."""
    return call_tool_and_expand(
        "build_governance_work_package",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-readiness-summary")
def governance_readiness_summary_route() -> dict[str, object]:
    """Return a lightweight description of readiness/remediation capability."""
    return {
        "message": "Use POST /jobs/assess-governance-readiness or /jobs/build-governance-work-package with workflow_result or file_path.",
        "dimensions": [
            "metadata_readiness",
            "mapping_readiness",
            "stg_readiness",
            "quality_rule_readiness",
            "review_completion_readiness",
        ],
    }


@router.post("/export-confirmation-workbooks")
def export_confirmation_workbooks_route(
    payload: GovernanceDeliveryPackageRequest,
) -> dict[str, object]:
    """Export local confirmation workbooks for governance review."""
    return call_tool_and_expand(
        "export_confirmation_workbooks",
        payload.model_dump(exclude_none=True),
    )


@router.post("/build-governance-delivery-package")
def build_governance_delivery_package_route(
    payload: GovernanceDeliveryPackageRequest,
) -> dict[str, object]:
    """Build a local governance delivery package with manifest and workbooks."""
    return call_tool_and_expand(
        "build_governance_delivery_package",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-delivery-manifest")
def governance_delivery_manifest_route() -> dict[str, object]:
    """Return a lightweight description of governance delivery package outputs."""
    return {
        "message": "Use POST /jobs/build-governance-delivery-package to generate a local package manifest.",
        "supported_artifacts": [
            "mapping_confirmation_workbook",
            "stg_confirmation_workbook",
            "quality_rule_confirmation_workbook",
            "backlog_workbook",
            "package_manifest",
        ],
        "boundary": "Local export only. No external distribution is triggered.",
    }


@router.post("/run-batch-governance")
def run_batch_governance_route(payload: BatchGovernanceRequest) -> dict[str, object]:
    """Run multi-file batch governance."""
    return call_tool_and_wrap(
        "run_batch_governance",
        payload.model_dump(exclude_none=True),
    )


@router.post("/run-incremental-rerun")
def run_incremental_rerun_route(payload: BatchGovernanceRequest) -> dict[str, object]:
    """Run changed-only batch governance."""
    return call_tool_and_wrap(
        "run_incremental_rerun",
        payload.model_dump(exclude_none=True),
    )


@router.post("/compare-governance-snapshots")
def compare_governance_snapshots_route(
    payload: BatchSnapshotCompareRequest,
) -> dict[str, object]:
    """Compare local governance batch snapshots."""
    return call_tool_and_expand(
        "compare_governance_snapshots",
        payload.model_dump(exclude_none=True),
    )


@router.get("/batch-snapshots/{batch_name}")
def batch_snapshots_route(batch_name: str) -> dict[str, object]:
    """List local batch snapshots for one batch name."""
    return {
        "batch_name": batch_name,
        "snapshots": list_batch_snapshots(batch_name),
    }


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
