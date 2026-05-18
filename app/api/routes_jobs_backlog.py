"""Backlog and portfolio job routes."""

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    GovernanceBacklogBuildRequest,
    GovernanceBacklogStatusUpdateRequest,
    GovernancePortfolioAssessmentRequest,
    ProgressSnapshotRequest,
)
from app.api.tool_response import call_tool_and_expand, call_tool_or_400
from app.core.models.tool_call_request import ToolCallRequest
from app.core.tools.tool_service import call_tool

router = APIRouter()


@router.post("/build-governance-backlog")
def build_governance_backlog_route(
    payload: GovernanceBacklogBuildRequest,
) -> dict[str, object]:
    """Build local governance backlog items."""
    return call_tool_and_expand(
        "build_governance_backlog",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-backlog")
def governance_backlog_route(
    status: str | None = None,
    priority: str | None = None,
    owner_role: str | None = None,
    gap_type: str | None = None,
) -> dict[str, object]:
    """List persisted governance backlog items with optional filters."""
    arguments = {
        key: value
        for key, value in {
            "status": status,
            "priority": priority,
            "owner_role": owner_role,
            "gap_type": gap_type,
        }.items()
        if value is not None
    }
    response = call_tool(
        ToolCallRequest(
            tool_name="list_governance_backlog_items",
            arguments=arguments,
        )
    )
    if response.status != "success":
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "message": response.message,
        "trace_id": response.trace_id,
        **(response.result or {}),
    }


@router.post("/governance-backlog/{backlog_id}/status")
def update_governance_backlog_status_route(
    backlog_id: str,
    payload: GovernanceBacklogStatusUpdateRequest,
) -> dict[str, object]:
    """Update one persisted backlog item status."""
    response = call_tool(
        ToolCallRequest(
            tool_name="update_governance_backlog_status",
            arguments={
                "backlog_id": backlog_id,
                "new_status": payload.new_status,
                "note": payload.note,
            },
        )
    )
    if response.status != "success":
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "message": response.message,
        "trace_id": response.trace_id,
        "update_result": response.result,
    }


@router.get("/governance-backlog-summary")
def governance_backlog_summary_route() -> dict[str, object]:
    """Return persisted governance backlog summary counts."""
    response = call_tool(
        ToolCallRequest(
            tool_name="list_governance_backlog_items",
            arguments={},
        )
    )
    if response.status != "success":
        raise HTTPException(status_code=400, detail=response.message)
    result = response.result or {}
    return {
        "message": "Governance backlog summary was loaded successfully.",
        "trace_id": response.trace_id,
        "backlog_summary": result.get("backlog_summary", {}),
    }


@router.post("/assess-governance-portfolio")
def assess_governance_portfolio_route(
    payload: GovernancePortfolioAssessmentRequest,
) -> dict[str, object]:
    """Assess backlog SLA, portfolio summary, and progress snapshot outputs."""
    return call_tool_and_expand(
        "assess_governance_portfolio",
        payload.model_dump(exclude_none=True),
    )


@router.post("/generate-progress-snapshot")
def generate_progress_snapshot_route(
    payload: ProgressSnapshotRequest,
) -> dict[str, object]:
    """Generate and optionally save a governance progress snapshot."""
    return call_tool_and_expand(
        "generate_progress_snapshot",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-progress-snapshots")
def governance_progress_snapshots_route() -> dict[str, object]:
    """List saved governance progress snapshots."""
    return call_tool_and_expand(
        "list_governance_progress_snapshots",
        {},
    )


@router.get("/governance-portfolio-summary")
def governance_portfolio_summary_route() -> dict[str, object]:
    """Return portfolio summary for persisted backlog items."""
    response = call_tool_or_400("assess_governance_portfolio", {})
    result = response.result or {}
    return {
        "message": "Governance portfolio summary was loaded successfully.",
        "trace_id": response.trace_id,
        "governance_portfolio_summary": result.get("governance_portfolio_summary", {}),
    }
