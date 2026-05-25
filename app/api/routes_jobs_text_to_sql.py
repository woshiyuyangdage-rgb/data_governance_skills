"""Text-to-SQL metadata readiness job routes."""

from fastapi import APIRouter

from app.api.job_requests import TextToSqlReadinessAssessmentRequest
from app.core.governance.text_to_sql_readiness_assessor import (
    TextToSqlReadinessAssessor,
)

router = APIRouter()


@router.post("/assess-text-to-sql-readiness")
def assess_text_to_sql_readiness_route(
    payload: TextToSqlReadinessAssessmentRequest,
) -> dict[str, object]:
    """Assess Text-to-SQL metadata readiness using local deterministic rules."""
    result = TextToSqlReadinessAssessor().assess(payload.tables)
    return {
        "message": "Text-to-SQL readiness assessment completed.",
        "text_to_sql_readiness_assessment": result.model_dump(),
        "text_to_sql_readiness_scores": [score.model_dump() for score in result.scores],
        "text_to_sql_readiness_issues": [issue.model_dump() for issue in result.issues],
        "text_to_sql_readiness_summary": dict(result.summary),
    }
