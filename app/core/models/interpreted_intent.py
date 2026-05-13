"""Model for one interpreted natural-language governance intent."""

from pydantic import BaseModel, Field


class InterpretedIntent(BaseModel):
    """Structured and explainable result of rule-based intent interpretation."""

    raw_text: str
    matched_intent_name: str | None = None
    matched_profile_name: str | None = None
    confidence: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    inferred_parameters: dict[str, object] = Field(default_factory=dict)
    fallback_used: bool = False
    message: str | None = None
