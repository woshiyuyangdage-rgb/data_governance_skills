"""Routes for report capability metadata."""

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/")
def list_reports() -> dict[str, object]:
    """Return the currently supported local report formats."""
    return {
        "message": "Local report export is available through the workflow report service and Streamlit workbench.",
        "items": ["excel", "markdown", "json"],
    }


@router.get("/supported-formats")
def supported_report_formats() -> dict[str, object]:
    """Return the currently supported report export formats."""
    return {
        "message": "The current MVP supports local JSON, Markdown, and Excel exports.",
        "items": ["excel", "markdown", "json"],
    }
