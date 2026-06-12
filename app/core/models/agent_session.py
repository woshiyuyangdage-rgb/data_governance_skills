"""Lightweight local session model for the agent shell."""

from pydantic import BaseModel, Field

from app.core.models.execution_plan import ExecutionPlan
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.tool_call_response import ToolCallResponse


class AgentSession(BaseModel):
    """Local single-user session state for plan preview and execution history."""

    session_id: str
    created_at: str | None = None
    recent_requests: list[str] = Field(default_factory=list)
    recent_plans: list[ExecutionPlan] = Field(default_factory=list)
    last_trace_id: str | None = None
    recent_trace_ids: list[str] = Field(default_factory=list)
    last_uploaded_file_path: str | None = None
    recent_uploaded_files: list[str] = Field(default_factory=list)
    last_exported_files: dict[str, str] = Field(default_factory=dict)
    last_task_request: GovernanceTaskRequest | None = None
    last_task_response: GovernanceTaskResponse | None = None
    last_tool_response: ToolCallResponse | None = None
