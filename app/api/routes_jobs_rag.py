"""RAG knowledge quality job routes."""

from fastapi import APIRouter

from app.api.job_requests import RagQualityAssessmentRequest
from app.core.knowledge.rag_quality_assessor import RagQualityAssessor

router = APIRouter()


@router.post("/assess-rag-quality")
def assess_rag_quality_route(
    payload: RagQualityAssessmentRequest,
) -> dict[str, object]:
    """Assess RAG knowledge-base quality using local deterministic rules."""
    result = RagQualityAssessor().assess(
        documents=payload.documents,
        chunks=payload.chunks,
        retrieval_logs=payload.retrieval_logs,
        answer_evaluations=payload.answer_evaluations,
    )
    return {
        "message": "RAG knowledge quality assessment completed.",
        "rag_quality_assessment": result.model_dump(),
        "rag_quality_issues": [issue.model_dump() for issue in result.issues],
        "rag_quality_summary": dict(result.summary),
    }
