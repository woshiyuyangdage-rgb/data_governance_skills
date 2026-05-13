"""Result model for context-based parameter resolution."""

from pydantic import BaseModel

from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.resolved_context import ResolvedContext


class ParameterResolutionResult(BaseModel):
    """Bundle original and resolved task requests with context metadata."""

    original_task_request: GovernanceTaskRequest
    resolved_task_request: GovernanceTaskRequest
    resolved_context: ResolvedContext
    resolution_applied: bool = False
