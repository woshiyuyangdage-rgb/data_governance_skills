"""Models for rule-based standard mapping recommendations."""

from pydantic import BaseModel, Field


class MappingResult(BaseModel):
    """Recommended standard mapping for one metadata field."""

    table_name: str
    field_name: str
    recommended_standard_code: str | None = None
    recommended_standard_name: str | None = None
    recommended_standard_name_cn: str | None = None
    match_score: float = 0.0
    match_reason: str = ""
    score_breakdown: dict[str, object] = Field(default_factory=dict)
    risk_hint: str | None = None
    action_suggestion: str | None = None
    requires_manual_review: bool = False
    mapping_status: str | None = None
    context_evidence: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    confirmed_source: str | None = None
    review_action: str | None = None
    reviewer_note: str | None = None
    top_candidates: list[dict[str, object]] = Field(default_factory=list)


class UnmappedField(BaseModel):
    """Field that could not be mapped confidently to a standard field."""

    table_name: str
    field_name: str
    field_name_cn: str | None = None
    best_candidate_code: str | None = None
    best_candidate_score: float | None = None
    reason: str = ""
    risk_hint: str | None = None
    action_suggestion: str | None = None
    requires_manual_review: bool = False
    evidence: list[str] = Field(default_factory=list)
