"""Domain pack match result model."""

from pydantic import BaseModel, Field


class DomainPackMatchResult(BaseModel):
    """Explainable domain pack match result."""

    matched_pack_name: str | None = None
    confidence: float | None = None
    matched_tokens: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    message: str | None = None

