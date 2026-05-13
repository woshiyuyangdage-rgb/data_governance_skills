"""Models for aggregated human review statistics."""

from pydantic import BaseModel


class ReviewSummary(BaseModel):
    """Aggregated counts for applied or saved review actions."""

    accepted_count: int = 0
    rejected_count: int = 0
    edited_count: int = 0
    manual_review_count: int = 0
    total_reviewed_count: int = 0
