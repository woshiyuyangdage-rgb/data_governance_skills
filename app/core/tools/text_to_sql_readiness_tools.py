"""Tool handlers for local Text-to-SQL metadata readiness assessment."""

from app.core.governance.text_to_sql_readiness_assessor import (
    TextToSqlReadinessAssessor,
)
from app.core.models.text_to_sql_readiness import TextToSqlTableMetadata
from app.core.models.tool_call_response import ToolCallResponse


def _coerce_tables(payload: object) -> list[TextToSqlTableMetadata]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("TextToSqlTableMetadata payload must be a list.")
    return [
        item if isinstance(item, TextToSqlTableMetadata) else TextToSqlTableMetadata.model_validate(item)
        for item in payload
    ]


class TextToSqlReadinessToolMixin:
    """Tool handler for Text-to-SQL metadata readiness checks."""

    def assess_text_to_sql_readiness(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Assess whether table metadata is ready for Text-to-SQL consumption."""
        tool_name = "assess_text_to_sql_readiness"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="text_to_sql_readiness_assessment",
        )
        try:
            tables = _coerce_tables(arguments.get("tables"))
            assessment = TextToSqlReadinessAssessor().assess(tables)
            result_payload = {
                "text_to_sql_readiness_assessment": assessment.model_dump(),
                "text_to_sql_readiness_scores": [
                    score.model_dump() for score in assessment.scores
                ],
                "text_to_sql_readiness_issues": [
                    issue.model_dump() for issue in assessment.issues
                ],
                "text_to_sql_readiness_summary": dict(assessment.summary),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Text-to-SQL readiness assessment completed.",
                operation="text_to_sql_readiness_assessment",
                notes=[
                    f"text_to_sql_issue_count={assessment.issue_count}",
                    f"table_count={assessment.table_count}",
                ],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Text-to-SQL readiness assessment completed.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to assess Text-to-SQL readiness: {exc}",
                operation="text_to_sql_readiness_assessment",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to assess Text-to-SQL readiness.",
                None,
                trace,
            )
