"""Aggregated review, quality-rule export, and package job routes."""

from fastapi import APIRouter

from app.api.routes_jobs_quality_execution import (
    _resolve_execution_ready_package_from_payload,
    build_execution_ready_package_route,
    export_execution_ready_package_route,
    router as execution_router,
)
from app.api.routes_jobs_quality_export import (
    export_confirmed_quality_rules_route,
    router as export_router,
)
from app.api.routes_jobs_quality_review import (
    list_review_summary,
    review_quality_rules_route,
    router as review_router,
    save_mapping_review,
    save_stg_review,
)
from app.api.routes_jobs_quality_summary import (
    execution_package_summary_route,
    quality_rule_review_summary_route,
    router as summary_router,
)

router = APIRouter()
router.include_router(review_router)
router.include_router(export_router)
router.include_router(execution_router)
router.include_router(summary_router)

__all__ = [
    "_resolve_execution_ready_package_from_payload",
    "build_execution_ready_package_route",
    "execution_package_summary_route",
    "export_confirmed_quality_rules_route",
    "export_execution_ready_package_route",
    "list_review_summary",
    "quality_rule_review_summary_route",
    "review_quality_rules_route",
    "router",
    "save_mapping_review",
    "save_stg_review",
]
