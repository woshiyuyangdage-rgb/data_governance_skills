"""Unified task service built on top of the governance router."""

from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.orchestrator.governance_router import GovernanceTaskRouter


def run_governance_task(request: GovernanceTaskRequest) -> GovernanceTaskResponse:
    """Run one governance task request through the shared router."""
    router = GovernanceTaskRouter()
    return router.run_task(request)


def run_governance_task_from_dict(payload: dict[str, object]) -> GovernanceTaskResponse:
    """Parse a dictionary payload into a task request and execute it."""
    request = GovernanceTaskRequest.model_validate(payload)
    return run_governance_task(request)


# TODO: expose this service through future planner or tool-calling layers once rule-based profile routing is stable.
