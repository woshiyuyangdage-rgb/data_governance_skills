"""Combined result model for agent shell preview and execution."""

from pydantic import BaseModel

from app.core.models.execution_plan import ExecutionPlan
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.interpreted_intent import InterpretedIntent
from app.core.models.resolved_context import ResolvedContext


class AgentShellResult(BaseModel):
    """Result returned by the lightweight agent shell service."""

    interpreted_intent: InterpretedIntent
    task_request: GovernanceTaskRequest
    execution_plan: ExecutionPlan
    resolved_context: ResolvedContext | None = None
    resolution_applied: bool = False
    task_response: GovernanceTaskResponse | None = None
    session_id: str | None = None
    status: str
    message: str
