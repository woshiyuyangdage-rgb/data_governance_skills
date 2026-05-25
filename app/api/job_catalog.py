"""Static route catalog for governance jobs."""

from app.api.job_catalog_backlog import BACKLOG_JOB_ITEMS
from app.api.job_catalog_control_plane import CONTROL_PLANE_JOB_ITEMS
from app.api.job_catalog_core import CORE_JOB_ITEMS
from app.api.job_catalog_delivery import DELIVERY_JOB_ITEMS
from app.api.job_catalog_quality import (
    QUALITY_JOB_ITEMS,
    QUALITY_SUMMARY_JOB_ITEMS,
)
from app.api.job_catalog_rag import RAG_JOB_ITEMS
from app.api.job_catalog_text_to_sql import TEXT_TO_SQL_JOB_ITEMS
from app.api.job_catalog_tools import TOOL_JOB_ITEMS

CATALOG_MESSAGE = "Rule-based v1 governance jobs available in the current MVP."


def build_job_catalog() -> dict[str, object]:
    """Return the available governance job catalog."""
    return {
        "message": CATALOG_MESSAGE,
        "items": [
            *CORE_JOB_ITEMS,
            *TOOL_JOB_ITEMS,
            *CONTROL_PLANE_JOB_ITEMS,
            *QUALITY_JOB_ITEMS,
            *RAG_JOB_ITEMS,
            *TEXT_TO_SQL_JOB_ITEMS,
            *DELIVERY_JOB_ITEMS,
            *BACKLOG_JOB_ITEMS,
            *QUALITY_SUMMARY_JOB_ITEMS,
        ],
    }
