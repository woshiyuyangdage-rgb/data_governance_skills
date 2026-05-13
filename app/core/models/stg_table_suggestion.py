"""Models for STG table structure suggestions."""

from pydantic import BaseModel, Field

from app.core.models.stg_field_suggestion import StgFieldSuggestion


class StgTableSuggestion(BaseModel):
    """Recommended STG structure for one source table."""

    source_table_name: str
    recommended_stg_table_name: str
    recommended_stg_table_name_cn: str | None = None
    field_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    summary: str
    issue_flags: list[str] = Field(default_factory=list)
