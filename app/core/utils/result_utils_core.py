"""Core dataframe helpers for workflow results."""

from typing import Any

import pandas as pd

from app.core.models.governance_task import GovernanceTask
from app.core.models.issue import Issue
from app.core.models.semantic_enrichment_result import (
    FieldDescriptionSuggestion,
    TableSemanticSummary,
)


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
                "system_name": issue.system_name,
                "business_domain": issue.business_domain,
                "impact_scope": issue.impact_scope,
                "ai_risk": issue.ai_risk,
                "recommended_priority": issue.recommended_priority,
                "requires_manual_review": issue.requires_manual_review,
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


def field_description_suggestions_to_dataframe(
    suggestions: list[FieldDescriptionSuggestion],
) -> pd.DataFrame:
    """Convert field description suggestions to a stable dataframe."""
    records = []
    for suggestion in suggestions:
        records.append(
            {
                "table_name": suggestion.table_name,
                "field_name": suggestion.field_name,
                "field_name_cn": suggestion.field_name_cn,
                "original_description": suggestion.original_description,
                "generated_description": suggestion.generated_description,
                "optimized_description": suggestion.optimized_description,
                "confidence": suggestion.confidence,
                "quality_tags_joined": ", ".join(suggestion.quality_tags),
                "governance_action": suggestion.governance_action,
                "requires_manual_review": suggestion.requires_manual_review,
                "business_domain": suggestion.business_domain,
                "standard_code": suggestion.standard_code,
                "standard_name": suggestion.standard_name,
                "evidence_joined": " | ".join(suggestion.evidence),
            }
        )
    return pd.DataFrame(records)


def table_semantic_summaries_to_dataframe(
    summaries: list[TableSemanticSummary],
) -> pd.DataFrame:
    """Convert table semantic summaries to a stable dataframe."""
    records = []
    for summary in summaries:
        records.append(
            {
                "table_name": summary.table_name,
                "table_name_cn": summary.table_name_cn,
                "original_description": summary.original_description,
                "business_object": summary.business_object,
                "business_purpose": summary.business_purpose,
                "core_fields_joined": ", ".join(summary.core_fields),
                "applicable_scenarios_joined": ", ".join(
                    summary.applicable_scenarios
                ),
                "ai_usage_risks_joined": " | ".join(summary.ai_usage_risks),
                "recommended_actions_joined": " | ".join(
                    summary.recommended_actions
                ),
                "generated_summary": summary.generated_summary,
                "optimized_summary": summary.optimized_summary,
                "confidence": summary.confidence,
                "quality_tags_joined": ", ".join(summary.quality_tags),
                "governance_action": summary.governance_action,
                "requires_manual_review": summary.requires_manual_review,
                "business_domain": summary.business_domain,
                "key_concepts_joined": ", ".join(summary.key_concepts),
                "evidence_joined": " | ".join(summary.evidence),
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
