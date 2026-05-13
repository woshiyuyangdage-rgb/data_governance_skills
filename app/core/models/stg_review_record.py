"""Models for human review of STG field suggestions."""

from pydantic import BaseModel


class StgReviewRecord(BaseModel):
    """One persisted human review record for an STG field suggestion."""

    source_table_name: str
    source_field_name: str
    original_recommended_stg_field_name: str | None = None
    final_stg_field_name: str | None = None
    original_recommended_data_type: str | None = None
    final_data_type: str | None = None
    review_action: str
    reviewer_note: str | None = None
    reviewed_at: str | None = None
    source: str
