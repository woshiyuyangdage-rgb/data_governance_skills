"""Tests for local RAG knowledge quality assessment."""

from app.core.knowledge.rag_quality_assessor import RagQualityAssessor
from app.core.models.rag_quality import (
    RagAnswerEvaluation,
    RagKnowledgeChunk,
    RagKnowledgeDocument,
    RagRetrievalLog,
)


def test_rag_quality_assessor_detects_document_chunk_retrieval_and_answer_issues() -> None:
    documents = [
        RagKnowledgeDocument(
            document_id="std_v1",
            title="Data Standard Policy",
            source="governance_portal",
            version="v1",
            updated_at="2020-01-01",
            status="active",
        ),
        RagKnowledgeDocument(
            document_id="std_v2",
            title="Data Standard Policy",
            source="governance_portal",
            version="v2",
            updated_at="2026-01-01",
            status="active",
            business_domain="governance",
            permission_label="internal",
            owner_department="data office",
            effective_date="2026-01-01",
            category="standard",
        ),
        RagKnowledgeDocument(
            document_id="perm_old",
            title="Permission Policy",
            source="wiki",
            version="v1",
            updated_at="2025-01-01",
            status="deprecated",
            permission_label="public",
        ),
    ]
    chunks = [
        RagKnowledgeChunk(
            chunk_id="chunk_short",
            document_id="std_v1",
            content="Customer id.",
        ),
        RagKnowledgeChunk(
            chunk_id="chunk_table",
            document_id="std_v2",
            content="field | type | desc | owner",
            permission_label="internal",
        ),
        RagKnowledgeChunk(
            chunk_id="chunk_sensitive",
            document_id="perm_old",
            content="confidential approval rule for restricted users",
            permission_label="public",
            embedding_id="emb-sensitive",
        ),
    ]
    retrieval_logs = [
        RagRetrievalLog(
            query_id="q1",
            query_text="What is the active data standard?",
            retrieved_document_id="std_v1",
            rank=1,
            score=0.3,
            expected_document_id="std_v2",
            is_relevant=False,
            user_permission_label="public",
            retrieved_permission_label="restricted",
        ),
        RagRetrievalLog(
            query_id="q1",
            query_text="What is the active data standard?",
            retrieved_document_id="perm_old",
            rank=2,
            expected_document_id="std_v2",
        ),
    ]
    answers = [
        RagAnswerEvaluation(
            query_id="q1",
            answer_text="Use the old standard.",
            cited_document_ids=[],
            expected_document_ids=["std_v2"],
            faithfulness_score=0.4,
            hallucination_flag=True,
        )
    ]

    result = RagQualityAssessor().assess(
        documents=documents,
        chunks=chunks,
        retrieval_logs=retrieval_logs,
        answer_evaluations=answers,
    )

    issue_types = {issue.issue_type for issue in result.issues}
    assert "stale_document" in issue_types
    assert "outdated_duplicate_version" in issue_types
    assert "deprecated_document_indexed" in issue_types
    assert "chunk_too_short" in issue_types
    assert "table_chunk_fragmented" in issue_types
    assert "sensitive_chunk_public" in issue_types
    assert "top1_wrong_document" in issue_types
    assert "retrieval_permission_leak" in issue_types
    assert "answer_missing_citation" in issue_types
    assert "low_answer_faithfulness" in issue_types
    assert result.summary["critical_or_high_issue_count"] >= 1


def test_rag_quality_assessor_accepts_clean_minimal_inputs() -> None:
    result = RagQualityAssessor().assess(
        documents=[
            RagKnowledgeDocument(
                document_id="std_v2",
                title="Data Standard Policy",
                source="governance_portal",
                version="v2",
                updated_at="2026-01-01",
                category="standard",
                business_domain="governance",
                permission_label="internal",
                owner_department="data office",
                effective_date="2026-01-01",
                status="active",
            )
        ],
        chunks=[
            RagKnowledgeChunk(
                chunk_id="chunk_1",
                document_id="std_v2",
                content=(
                    "Customer ID is the unique identifier for customer entities. "
                    "Use this standard when binding customer-related fields."
                ),
                title="Data Standard Policy",
                permission_label="internal",
                embedding_id="emb-1",
            )
        ],
        retrieval_logs=[
            RagRetrievalLog(
                query_id="q1",
                query_text="Which standard identifies customers?",
                retrieved_document_id="std_v2",
                rank=1,
                score=0.88,
                expected_document_id="std_v2",
                is_relevant=True,
                user_permission_label="internal",
                retrieved_permission_label="internal",
            )
        ],
        answer_evaluations=[
            RagAnswerEvaluation(
                query_id="q1",
                answer_text="Use Customer ID.",
                cited_document_ids=["std_v2"],
                expected_document_ids=["std_v2"],
                faithfulness_score=0.95,
            )
        ],
    )

    assert result.issue_count == 0
    assert result.summary["issue_count"] == 0
