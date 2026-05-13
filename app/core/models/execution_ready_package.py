"""Execution-ready governance package model."""

from typing import Any

from pydantic import BaseModel, Field

from app.core.models.execution_ready_rule import ExecutionReadyRule


class ExecutionReadyPackage(BaseModel):
    """Stable rule package contract for future execution adapters."""

    package_id: str
    generated_at: str | None = None
    package_name: str
    rule_count: int
    source_profile: str | None = None
    rules: list[ExecutionReadyRule] = Field(default_factory=list)
    compatibility: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
