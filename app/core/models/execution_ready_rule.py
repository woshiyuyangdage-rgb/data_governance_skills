"""Execution-ready rule model for the package intermediate layer."""

from typing import Any

from pydantic import BaseModel, Field


class ExecutionReadyRule(BaseModel):
    """Confirmed quality rule enriched with execution contract metadata."""

    rule_id: str
    source_table_name: str
    source_field_name: str
    target_field_name: str | None = None
    rule_type: str
    semantic_type: str | None = None
    rule_expression: str | None = None
    execution_expression: str | None = None
    execution_mode: str | None = None
    severity: str
    priority: str | None = None
    rule_scope: str = "field"
    field_group: list[str] = Field(default_factory=list)
    confidence: float | None = None
    review_priority: str | None = None
    confirmation_source: str | None = None
    match_basis: str | None = None
    reason: str | None = None
    engine_hints: dict[str, Any] = Field(default_factory=dict)
    trace_metadata: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
