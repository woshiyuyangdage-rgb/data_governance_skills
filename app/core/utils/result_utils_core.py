"""Core dataframe helpers for workflow results."""

from typing import Any

import pandas as pd

from app.core.models.governance_task import GovernanceTask
from app.core.models.issue import Issue


def _model_to_dict(model: object) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return {"value": str(model)}


def issues_to_dataframe(issues: list[Issue]) -> pd.DataFrame:
    """Convert issues to a stable report-friendly dataframe."""
    records = []
    for issue in issues:
        records.append(
            {
                "issue_id": issue.issue_id,
                "object_type": issue.object_type,
                "object_name": issue.object_name,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "suggestion": issue.suggestion,
                "confidence": issue.confidence,
                "evidence_joined": " | ".join(issue.evidence),
            }
        )
    return pd.DataFrame(records)


def tasks_to_dataframe(tasks: list[GovernanceTask]) -> pd.DataFrame:
    """Convert governance tasks to a stable dataframe."""
    records = []
    for task in tasks:
        records.append(
            {
                "task_id": task.task_id,
                "issue_ids_joined": ", ".join(task.issue_ids),
                "priority": task.priority,
                "action": task.action,
                "suggested_owner_role": task.suggested_owner_role,
                "acceptance_criteria": task.acceptance_criteria,
            }
        )
    return pd.DataFrame(records)


def skill_outputs_to_dataframe(skill_outputs: dict[str, Any]) -> pd.DataFrame:
    """Summarize skill outputs for UI and report export."""
    records = []
    for skill_name, payload in skill_outputs.items():
        payload_dict = payload if isinstance(payload, dict) else _model_to_dict(payload)
        records.append(
            {
                "skill_name": skill_name,
                "summary": payload_dict.get("summary", ""),
            }
        )
    return pd.DataFrame(records)

