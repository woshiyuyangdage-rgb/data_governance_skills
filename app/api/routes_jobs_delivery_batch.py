"""Batch and incremental governance job routes."""

from fastapi import APIRouter

from app.api.job_requests import BatchGovernanceRequest, BatchSnapshotCompareRequest
from app.api.tool_response import call_tool_and_expand, call_tool_and_wrap
from app.core.governance.batch_snapshot_store import list_batch_snapshots

router = APIRouter()


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
