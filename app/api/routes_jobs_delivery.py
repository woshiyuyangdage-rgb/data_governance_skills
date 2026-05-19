"""Aggregated readiness, delivery, batch, and confirmation job routes."""

from fastapi import APIRouter

from app.api.routes_jobs_delivery_batch import (
    batch_snapshots_route,
    compare_governance_snapshots_route,
    router as batch_router,
    run_batch_governance_route,
    run_incremental_rerun_route,
)
from app.api.routes_jobs_delivery_confirmation import (
    import_confirmation_and_rerun_route,
    import_confirmation_workbook_route,
    roundtrip_changed_objects_summary_route,
    router as confirmation_router,
    validate_confirmation_workbook_route,
)
from app.api.routes_jobs_delivery_package import (
    build_governance_delivery_package_route,
    export_confirmation_workbooks_route,
    governance_delivery_manifest_route,
    router as package_router,
)
from app.api.routes_jobs_delivery_readiness import (
    assess_governance_readiness_route,
    build_governance_work_package_route,
    governance_readiness_summary_route,
    router as readiness_router,
)

router = APIRouter()
router.include_router(readiness_router)
router.include_router(package_router)
router.include_router(batch_router)
router.include_router(confirmation_router)

__all__ = [
    "assess_governance_readiness_route",
    "batch_snapshots_route",
    "build_governance_delivery_package_route",
    "build_governance_work_package_route",
    "compare_governance_snapshots_route",
    "export_confirmation_workbooks_route",
    "governance_delivery_manifest_route",
    "governance_readiness_summary_route",
    "import_confirmation_and_rerun_route",
    "import_confirmation_workbook_route",
    "roundtrip_changed_objects_summary_route",
    "router",
    "run_batch_governance_route",
    "run_incremental_rerun_route",
    "validate_confirmation_workbook_route",
]
