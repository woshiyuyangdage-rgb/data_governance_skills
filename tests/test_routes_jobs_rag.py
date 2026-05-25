"""Route tests for RAG knowledge quality assessment."""

from app.api.routes_jobs import RagQualityAssessmentRequest, assess_rag_quality_route
from app.core.models.rag_quality import RagKnowledgeChunk, RagKnowledgeDocument


def test_assess_rag_quality_route_returns_structured_issues() -> None:
    response = assess_rag_quality_route(
        RagQualityAssessmentRequest(
            documents=[
                RagKnowledgeDocument(
                    document_id="policy_v1",
                    title="Permission Policy",
                    source="wiki",
                    version="v1",
                    status="deprecated",
                )
            ],
            chunks=[
                RagKnowledgeChunk(
                    chunk_id="chunk_1",
                    document_id="policy_v1",
                    content="secret rule",
                    permission_label="public",
                )
            ],
        )
    )

    assert response["rag_quality_summary"]["issue_count"] >= 1
    assert response["rag_quality_issues"]
    assert response["rag_quality_assessment"]["document_count"] == 1
