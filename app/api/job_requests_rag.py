"""Request models for RAG knowledge quality assessment."""

from pydantic import BaseModel, Field

from app.core.models.rag_quality import (
    RagAnswerEvaluation,
    RagKnowledgeChunk,
    RagKnowledgeDocument,
    RagRetrievalLog,
)


class RagQualityAssessmentRequest(BaseModel):
    """Request body for local RAG knowledge quality assessment."""

    documents: list[RagKnowledgeDocument] = Field(default_factory=list)
    chunks: list[RagKnowledgeChunk] = Field(default_factory=list)
    retrieval_logs: list[RagRetrievalLog] = Field(default_factory=list)
    answer_evaluations: list[RagAnswerEvaluation] = Field(default_factory=list)
