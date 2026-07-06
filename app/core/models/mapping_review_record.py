"""Models for human review of mapping recommendations."""

from pydantic import BaseModel


class MappingReviewRecord(BaseModel):
    """One persisted human review record for a mapping suggestion."""

    table_name: str
    field_name: str
    original_recommended_standard_code: str | None = None
    final_standard_code: str | None = None
    review_action: str
    reviewer_note: str | None = None
    reviewed_at: str | None = None
    source: str
    dictionary_version: str | None = None
    standard_set_version: str | None = None
    config_fingerprint: str | None = None
    source_field_hash: str | None = None
