"""Remediation action model."""

from pydantic import BaseModel


class RemediationAction(BaseModel):
    """Recommended governance remediation action."""

    object_type: str
    object_name: str
    gap_type: str
    action: str
    owner_role: str
    priority: str
    expected_output: str | None = None
    dependency_notes: str | None = None
    reason: str | None = None
