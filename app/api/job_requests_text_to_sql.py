"""Request models for Text-to-SQL metadata readiness assessment."""

from pydantic import BaseModel, Field

from app.core.models.text_to_sql_readiness import TextToSqlTableMetadata


class TextToSqlReadinessAssessmentRequest(BaseModel):
    """Request body for local Text-to-SQL readiness assessment."""

    tables: list[TextToSqlTableMetadata] = Field(default_factory=list)
