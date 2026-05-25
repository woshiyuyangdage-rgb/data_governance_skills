"""Models for local RAG knowledge-base quality assessment."""

from pydantic import BaseModel, Field


class RagKnowledgeDocument(BaseModel):
    """Document-level metadata for RAG readiness checks."""

    document_id: str
    title: str | None = None
    source: str | None = None
    version: str | None = None
    updated_at: str | None = None
    category: str | None = None
    business_domain: str | None = None
    permission_label: str | None = None
    owner_department: str | None = None
    effective_date: str | None = None
    status: str | None = None
    content: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RagKnowledgeChunk(BaseModel):
    """Chunk-level payload used by RAG retrieval systems."""

    chunk_id: str
    document_id: str
    content: str
    title: str | None = None
    source: str | None = None
    version: str | None = None
    business_domain: str | None = None
    permission_label: str | None = None
    token_count: int | None = None
    chunk_index: int | None = None
    embedding_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RagRetrievalLog(BaseModel):
    """One retrieval result row for a RAG evaluation query."""

    query_id: str
    query_text: str
    retrieved_chunk_id: str | None = None
    retrieved_document_id: str | None = None
    rank: int | None = None
    score: float | None = None
    expected_document_id: str | None = None
    is_relevant: bool | None = None
    user_permission_label: str | None = None
    retrieved_permission_label: str | None = None


class RagAnswerEvaluation(BaseModel):
    """Answer-level evaluation signal for RAG generation quality."""

    query_id: str
    answer_text: str
    cited_document_ids: list[str] = Field(default_factory=list)
    expected_document_ids: list[str] = Field(default_factory=list)
    faithfulness_score: float | None = None
    hallucination_flag: bool | None = None
    mixed_policy_flag: bool | None = None
    overextended_flag: bool | None = None
    exposes_sensitive_content: bool | None = None
    user_feedback: str | None = None


class RagQualityIssue(BaseModel):
    """Structured issue found during RAG knowledge-base quality assessment."""

    object_type: str
    object_name: str
    issue_type: str
    severity: str
    evidence: list[str] = Field(default_factory=list)
    risk: str | None = None
    suggestion: str | None = None
    requires_manual_review: bool = False
    category: str | None = None
    business_domain: str | None = None


class RagQualityAssessmentResult(BaseModel):
    """RAG knowledge-base quality assessment output."""

    document_count: int = 0
    chunk_count: int = 0
    retrieval_log_count: int = 0
    answer_evaluation_count: int = 0
    issue_count: int = 0
    issues: list[RagQualityIssue] = Field(default_factory=list)
    summary: dict[str, object] = Field(default_factory=dict)
