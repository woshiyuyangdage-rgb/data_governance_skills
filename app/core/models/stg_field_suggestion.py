"""Models for STG field structure suggestions."""

from pydantic import BaseModel, Field


class StgFieldSuggestion(BaseModel):
    """Recommended STG field structure for one source field."""

    source_table_name: str
    source_field_name: str
    source_field_name_cn: str | None = None
    source_data_type: str | None = None
    recommended_stg_field_name: str
    recommended_stg_field_name_cn: str | None = None
    recommended_data_type: str | None = None
    nullable: bool | None = None
    mapping_source: str
    match_score: float | None = None
    recommendation_evidence: dict[str, object] = Field(default_factory=dict)
    action: str
    notes: str | None = None
    confirmed_source: str | None = None
    review_action: str | None = None
    reviewer_note: str | None = None
