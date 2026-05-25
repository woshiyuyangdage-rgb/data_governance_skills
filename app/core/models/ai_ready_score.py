"""AI consumption readiness scoring model."""

from pydantic import BaseModel, Field


class AiReadyScore(BaseModel):
    """Table-level AI-ready score for RAG, Text-to-SQL, and data assistants."""

    object_type: str = "table"
    object_name: str
    overall_score: float = 0.0
    ai_ready_level: str = "D_not_recommended_for_ai"
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    summary: str | None = None
