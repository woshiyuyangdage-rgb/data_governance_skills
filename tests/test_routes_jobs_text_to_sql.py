"""Route tests for Text-to-SQL metadata readiness assessment."""

from app.api.routes_jobs import (
    TextToSqlReadinessAssessmentRequest,
    assess_text_to_sql_readiness_route,
)
from app.core.models.field_meta import FieldMeta
from app.core.models.text_to_sql_readiness import TextToSqlTableMetadata


def test_assess_text_to_sql_readiness_route_returns_structured_scores() -> None:
    response = assess_text_to_sql_readiness_route(
        TextToSqlReadinessAssessmentRequest(
            tables=[
                TextToSqlTableMetadata(
                    table_name="customer_ext",
                    table_description="x",
                    fields=[
                        FieldMeta(field_name="status", field_description="status"),
                    ],
                )
            ]
        )
    )

    assert response["message"] == "Text-to-SQL readiness assessment completed."
    assert response["text_to_sql_readiness_summary"]["table_count"] == 1
    assert response["text_to_sql_readiness_scores"]
    assert response["text_to_sql_readiness_issues"]
    assert response["text_to_sql_readiness_assessment"]["issue_count"] >= 1
