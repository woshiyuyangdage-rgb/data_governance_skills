"""Aggregated routes for governance job execution.

This module keeps the historical `app.api.routes_jobs` import surface while the
route implementations live in smaller domain-focused modules.
"""

from fastapi import APIRouter
from app.api.routes_jobs_backlog import router as backlog_router
from app.api.routes_jobs_core import router as core_router
from app.api.routes_jobs_control_plane import (
    router as control_plane_router,
)
from app.api.routes_jobs_delivery import router as delivery_router
from app.api.routes_jobs_intake import router as intake_router
from app.api.routes_jobs_quality import router as quality_router
from app.api.routes_jobs_tools import router as tools_router

router = APIRouter(prefix="/jobs", tags=["jobs"])
router.include_router(intake_router)
router.include_router(core_router)
router.include_router(tools_router)
router.include_router(control_plane_router)
router.include_router(quality_router)
router.include_router(delivery_router)
router.include_router(backlog_router)
