"""Summary quality job routes."""

from fastapi import APIRouter

from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.review.quality_review_service import summarize_quality_rule_review_records

router = APIRouter()


@router.get("/execution-package-summary")
def execution_package_summary_route() -> dict[str, object]:
    """Return a lightweight description of the execution-ready package capability."""
    return {
        "message": "Use POST /jobs/build-execution-ready-package with confirmed rules or file_path to build a package summary.",
        "supported_export_formats": ["package_json", "package_manifest", "dbt_yaml"],
    }


@router.get("/quality-rule-review-summary")
def quality_rule_review_summary_route() -> dict[str, object]:
    """Return quality rule review counts from stored overrides."""
    records = load_quality_rule_overrides()
    return summarize_quality_rule_review_records(records, confirmed_count=0)
