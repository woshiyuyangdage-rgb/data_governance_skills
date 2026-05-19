"""Governance delivery package job routes."""

from fastapi import APIRouter

from app.api.job_requests import GovernanceDeliveryPackageRequest
from app.api.tool_response import call_tool_and_expand

router = APIRouter()


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
