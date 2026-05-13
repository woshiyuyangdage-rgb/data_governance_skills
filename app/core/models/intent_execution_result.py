"""Combined result for intent interpretation and optional execution."""

from pydantic import BaseModel

from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.interpreted_intent import InterpretedIntent


class IntentExecutionResult(BaseModel):
    """Natural-language intent interpretation result plus downstream task artifacts."""

    interpreted_intent: InterpretedIntent
    task_request: GovernanceTaskRequest
    task_response: GovernanceTaskResponse | None = None
