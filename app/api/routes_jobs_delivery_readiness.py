"""Readiness and work-package job routes."""

from fastapi import APIRouter

from app.api.job_requests import (
    GovernanceReadinessAssessmentRequest,
    GovernanceWorkPackageBuildRequest,
)
from app.api.tool_response import call_tool_and_expand

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
