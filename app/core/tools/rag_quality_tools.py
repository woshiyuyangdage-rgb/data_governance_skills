"""Tool handlers for local RAG knowledge quality assessment."""

from app.core.knowledge.rag_quality_assessor import RagQualityAssessor
from app.core.models.rag_quality import (
    RagAnswerEvaluation,
    RagKnowledgeChunk,
    RagKnowledgeDocument,
    RagRetrievalLog,
)
from app.core.models.tool_call_response import ToolCallResponse


def _coerce_list(payload: object, model_cls: type) -> list[object]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError(f"{model_cls.__name__} payload must be a list.")
    return [
        item if isinstance(item, model_cls) else model_cls.model_validate(item)
        for item in payload
    ]


class RagQualityToolMixin:
    """Tool handler for RAG knowledge-base quality checks."""

    def assess_rag_quality(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Assess RAG documents, chunks, retrieval logs, answers, and permissions."""
        tool_name = "assess_rag_quality"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="rag_quality_assessment",
        )
        try:
            documents = _coerce_list(arguments.get("documents"), RagKnowledgeDocument)
            chunks = _coerce_list(arguments.get("chunks"), RagKnowledgeChunk)
            retrieval_logs = _coerce_list(arguments.get("retrieval_logs"), RagRetrievalLog)
            answer_evaluations = _coerce_list(
                arguments.get("answer_evaluations"),
                RagAnswerEvaluation,
            )
            assessment = RagQualityAssessor().assess(
                documents=documents,
                chunks=chunks,
                retrieval_logs=retrieval_logs,
                answer_evaluations=answer_evaluations,
            )
            result_payload = {
                "rag_quality_assessment": assessment.model_dump(),
                "rag_quality_issues": [
                    issue.model_dump() for issue in assessment.issues
                ],
                "rag_quality_summary": dict(assessment.summary),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "RAG knowledge quality assessment completed.",
                operation="rag_quality_assessment",
                notes=[
                    f"rag_quality_issue_count={assessment.issue_count}",
                    f"document_count={assessment.document_count}",
                    f"chunk_count={assessment.chunk_count}",
                ],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "RAG knowledge quality assessment completed.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to assess RAG quality: {exc}",
                operation="rag_quality_assessment",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to assess RAG quality.",
                None,
                trace,
            )
