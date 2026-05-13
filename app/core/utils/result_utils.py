"""Helpers for converting workflow results into dataframes."""

from typing import Any

import pandas as pd

from app.core.models.backlog_summary import BacklogSummary
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_portfolio_summary import GovernancePortfolioSummary
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.governance_task import GovernanceTask
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult, UnmappedField
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.progress_snapshot import ProgressSnapshot
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.models.review_summary import ReviewSummary
from app.core.models.rule_export_result import RuleExportResult
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_table_suggestion import StgTableSuggestion


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


def mapping_results_to_dataframe(mapping_results: list[MappingResult]) -> pd.DataFrame:
    """Convert mapping recommendations to a stable dataframe."""
    records = []
    for result in mapping_results:
        records.append(
            {
                "table_name": result.table_name,
                "field_name": result.field_name,
                "recommended_standard_code": result.recommended_standard_code,
                "recommended_standard_name": result.recommended_standard_name,
                "recommended_standard_name_cn": result.recommended_standard_name_cn,
                "match_score": result.match_score,
                "match_reason": result.match_reason,
                "candidate_count": result.candidate_count,
                "confirmed_source": result.confirmed_source,
                "review_action": result.review_action,
                "reviewer_note": result.reviewer_note,
            }
        )
    return pd.DataFrame(records)


def unmapped_fields_to_dataframe(unmapped_fields: list[UnmappedField]) -> pd.DataFrame:
    """Convert unmapped or low-confidence fields to a stable dataframe."""
    records = []
    for field in unmapped_fields:
        records.append(
            {
                "table_name": field.table_name,
                "field_name": field.field_name,
                "field_name_cn": field.field_name_cn,
                "best_candidate_code": field.best_candidate_code,
                "best_candidate_score": field.best_candidate_score,
                "reason": field.reason,
                "evidence_joined": " | ".join(field.evidence),
            }
        )
    return pd.DataFrame(records)


def stg_tables_to_dataframe(
    stg_suggestions: list[StgTableSuggestion],
) -> pd.DataFrame:
    """Convert STG table suggestions to a stable dataframe."""
    records = []
    for suggestion in stg_suggestions:
        records.append(
            {
                "source_table_name": suggestion.source_table_name,
                "recommended_stg_table_name": suggestion.recommended_stg_table_name,
                "recommended_stg_table_name_cn": suggestion.recommended_stg_table_name_cn,
                "summary": suggestion.summary,
                "issue_flags_joined": ", ".join(suggestion.issue_flags),
            }
        )
    return pd.DataFrame(records)


def stg_fields_to_dataframe(
    stg_field_suggestions: list[StgFieldSuggestion],
) -> pd.DataFrame:
    """Convert STG field suggestions to a stable dataframe."""
    records = []
    for suggestion in stg_field_suggestions:
        records.append(
            {
                "source_table_name": suggestion.source_table_name,
                "source_field_name": suggestion.source_field_name,
                "source_field_name_cn": suggestion.source_field_name_cn,
                "source_data_type": suggestion.source_data_type,
                "recommended_stg_field_name": suggestion.recommended_stg_field_name,
                "recommended_stg_field_name_cn": suggestion.recommended_stg_field_name_cn,
                "recommended_data_type": suggestion.recommended_data_type,
                "nullable": suggestion.nullable,
                "mapping_source": suggestion.mapping_source,
                "match_score": suggestion.match_score,
                "action": suggestion.action,
                "notes": suggestion.notes,
                "confirmed_source": suggestion.confirmed_source,
                "review_action": suggestion.review_action,
                "reviewer_note": suggestion.reviewer_note,
            }
        )
    return pd.DataFrame(records)


def quality_rules_to_dataframe(
    quality_rule_suggestions: list[QualityRuleSuggestion],
) -> pd.DataFrame:
    """Convert quality rule recommendations to a stable dataframe."""
    records = []
    for suggestion in quality_rule_suggestions:
        records.append(
            {
                "source_table_name": suggestion.source_table_name,
                "source_field_name": suggestion.source_field_name,
                "recommended_field_name": suggestion.recommended_field_name,
                "rule_type": suggestion.rule_type,
                "rule_expression": suggestion.rule_expression,
                "severity": suggestion.severity,
                "priority": suggestion.priority,
                "confidence": suggestion.confidence,
                "review_priority": suggestion.review_priority,
                "rule_scope": suggestion.rule_scope,
                "field_group": suggestion.field_group,
                "recommendation_source": suggestion.recommendation_source,
                "match_basis": suggestion.match_basis,
                "reason": suggestion.reason,
                "notes": suggestion.notes,
                "confirmed_source": suggestion.confirmed_source,
                "review_action": suggestion.review_action,
                "reviewer_note": suggestion.reviewer_note,
            }
        )
    return pd.DataFrame(records)


def quality_rule_packages_to_dataframe(
    quality_rule_packages: list[QualityRulePackage],
) -> pd.DataFrame:
    """Convert grouped quality rule packages to a stable dataframe."""
    records = []
    for package in quality_rule_packages:
        records.append(
            {
                "source_table_name": package.source_table_name,
                "field_rule_count": package.field_rule_count,
                "summary": package.summary,
            }
        )
    return pd.DataFrame(records)


def confirmed_quality_rules_to_dataframe(
    confirmed_quality_rules: list[ConfirmedQualityRule],
) -> pd.DataFrame:
    """Convert confirmed quality rules to a stable dataframe."""
    records = []
    for rule in confirmed_quality_rules:
        records.append(
            {
                "source_table_name": rule.source_table_name,
                "source_field_name": rule.source_field_name,
                "recommended_field_name": rule.recommended_field_name,
                "rule_type": rule.rule_type,
                "rule_expression": rule.rule_expression,
                "severity": rule.severity,
                "priority": rule.priority,
                "rule_scope": rule.rule_scope,
                "field_group": rule.field_group,
                "confidence": rule.confidence,
                "review_priority": rule.review_priority,
                "confirmation_source": rule.confirmation_source,
                "match_basis": rule.match_basis,
                "reason": rule.reason,
                "notes": rule.notes,
            }
        )
    return pd.DataFrame(records)


def cross_field_quality_rules_to_dataframe(
    cross_field_quality_rules: list[CrossFieldQualityRule],
) -> pd.DataFrame:
    """Convert cross-field quality rules to a stable dataframe."""
    records = []
    for rule in cross_field_quality_rules:
        records.append(
            {
                "source_table_name": rule.source_table_name,
                "field_group": rule.field_group,
                "rule_type": rule.rule_type,
                "rule_expression": rule.rule_expression,
                "severity": rule.severity,
                "priority": rule.priority,
                "confidence": rule.confidence,
                "review_priority": rule.review_priority,
                "recommendation_source": rule.recommendation_source,
                "match_basis": rule.match_basis,
                "reason": rule.reason,
                "notes": rule.notes,
            }
        )
    return pd.DataFrame(records)


def quality_rule_review_summary_to_dataframe(
    quality_rule_review_summary: dict[str, object] | None,
) -> pd.DataFrame:
    """Convert quality rule review summary into a one-row dataframe."""
    if not quality_rule_review_summary:
        return pd.DataFrame()
    return pd.DataFrame([dict(quality_rule_review_summary)])


def quality_review_queue_summary_to_dataframe(
    quality_review_queue_summary: dict[str, object] | None,
) -> pd.DataFrame:
    """Convert quality review queue summary into a one-row dataframe."""
    if not quality_review_queue_summary:
        return pd.DataFrame()
    return pd.DataFrame([dict(quality_review_queue_summary)])


def rule_export_results_to_dataframe(
    rule_export_results: list[RuleExportResult],
) -> pd.DataFrame:
    """Convert rule export results to a stable dataframe."""
    records = []
    for result in rule_export_results:
        records.append(
            {
                "export_format": result.export_format,
                "output_path": result.output_path,
                "rule_count": result.rule_count,
                "status": result.status,
                "message": result.message,
            }
        )
    return pd.DataFrame(records)


def execution_ready_rules_to_dataframe(
    execution_ready_package: ExecutionReadyPackage | None,
) -> pd.DataFrame:
    """Convert execution-ready package rules to a stable dataframe."""
    if execution_ready_package is None:
        return pd.DataFrame()
    records = []
    for rule in execution_ready_package.rules:
        records.append(
            {
                "package_id": execution_ready_package.package_id,
                "rule_id": rule.rule_id,
                "source_table_name": rule.source_table_name,
                "source_field_name": rule.source_field_name,
                "target_field_name": rule.target_field_name,
                "rule_type": rule.rule_type,
                "rule_scope": rule.rule_scope,
                "field_group": rule.field_group,
                "semantic_type": rule.semantic_type,
                "rule_expression": rule.rule_expression,
                "execution_expression": rule.execution_expression,
                "execution_mode": rule.execution_mode,
                "severity": rule.severity,
                "priority": rule.priority,
                "confidence": rule.confidence,
                "review_priority": rule.review_priority,
                "confirmation_source": rule.confirmation_source,
                "match_basis": rule.match_basis,
                "reason": rule.reason,
                "engine_hints": rule.engine_hints,
                "notes": rule.notes,
            }
        )
    return pd.DataFrame(records)


def execution_package_summary_to_dataframe(
    execution_ready_package: ExecutionReadyPackage | None,
    execution_package_summary: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Convert execution package summary into a one-row dataframe."""
    if execution_package_summary:
        return pd.DataFrame([dict(execution_package_summary)])
    if execution_ready_package is None:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "package_id": execution_ready_package.package_id,
                "package_name": execution_ready_package.package_name,
                "rule_count": execution_ready_package.rule_count,
                "source_profile": execution_ready_package.source_profile,
                "compatibility": execution_ready_package.compatibility,
                "summary": execution_ready_package.summary,
            }
        ]
    )


def execution_package_export_results_to_dataframe(
    export_results: list[ExecutionPackageExportResult],
) -> pd.DataFrame:
    """Convert execution package export results to a stable dataframe."""
    records = []
    for result in export_results:
        records.append(
            {
                "export_format": result.export_format,
                "output_path": result.output_path,
                "package_id": result.package_id,
                "rule_count": result.rule_count,
                "status": result.status,
                "message": result.message,
            }
        )
    return pd.DataFrame(records)


def readiness_scores_to_dataframe(
    readiness_scores: list[ReadinessScore],
) -> pd.DataFrame:
    """Convert readiness scores to a stable dataframe."""
    records = []
    for score in readiness_scores:
        payload = {
            "object_type": score.object_type,
            "object_name": score.object_name,
            "overall_score": score.overall_score,
            "readiness_level": score.readiness_level,
            "summary": score.summary,
        }
        for key, value in score.dimension_scores.items():
            payload[key] = value
        records.append(payload)
    return pd.DataFrame(records)


def governance_gaps_to_dataframe(
    governance_gaps: list[GovernanceGap],
) -> pd.DataFrame:
    """Convert governance gaps to a stable dataframe."""
    records = []
    for gap in governance_gaps:
        records.append(
            {
                "object_type": gap.object_type,
                "object_name": gap.object_name,
                "gap_type": gap.gap_type,
                "category": gap.category,
                "severity": gap.severity,
                "source_signals": gap.source_signals,
                "reason": gap.reason,
                "suggested_owner_role": gap.suggested_owner_role,
            }
        )
    return pd.DataFrame(records)


def remediation_actions_to_dataframe(
    remediation_actions: list[RemediationAction],
) -> pd.DataFrame:
    """Convert remediation actions to a stable dataframe."""
    records = []
    for action in remediation_actions:
        records.append(
            {
                "object_type": action.object_type,
                "object_name": action.object_name,
                "gap_type": action.gap_type,
                "action": action.action,
                "owner_role": action.owner_role,
                "priority": action.priority,
                "expected_output": action.expected_output,
                "dependency_notes": action.dependency_notes,
                "reason": action.reason,
            }
        )
    return pd.DataFrame(records)


def governance_work_package_summary_to_dataframe(
    work_package: GovernanceWorkPackage | None,
    readiness_summary: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Convert governance work package metadata into a one-row dataframe."""
    if work_package is None and not readiness_summary:
        return pd.DataFrame()
    payload = dict(readiness_summary or {})
    if work_package is not None:
        payload.update(
            {
                "package_name": work_package.package_name,
                "generated_at": work_package.generated_at,
                "readiness_score_count": len(work_package.readiness_scores),
                "gap_count": len(work_package.governance_gaps),
                "remediation_action_count": len(work_package.remediation_actions),
                "summary": work_package.summary,
            }
        )
    return pd.DataFrame([payload])


def governance_backlog_items_to_dataframe(
    backlog_items: list[GovernanceBacklogItem],
) -> pd.DataFrame:
    """Convert governance backlog items to a stable dataframe."""
    records = []
    for item in backlog_items:
        records.append(
            {
                "backlog_id": item.backlog_id,
                "object_type": item.object_type,
                "object_name": item.object_name,
                "gap_type": item.gap_type,
                "category": item.category,
                "action": item.action,
                "owner_role": item.owner_role,
                "priority": item.priority,
                "status": item.status,
                "urgency_score": item.urgency_score,
                "dependency_notes": item.dependency_notes,
                "blocked_by": item.blocked_by,
                "completion_criteria": item.completion_criteria,
                "expected_output": item.expected_output,
                "reason": item.reason,
                "source_signals": item.source_signals,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "notes": item.notes,
            }
        )
    return pd.DataFrame(records)


def backlog_summary_to_dataframe(
    backlog_summary: BacklogSummary | None,
) -> pd.DataFrame:
    """Convert backlog summary into a one-row dataframe."""
    if backlog_summary is None:
        return pd.DataFrame()
    return pd.DataFrame([backlog_summary.model_dump()])


def backlog_sla_statuses_to_dataframe(
    statuses: list[BacklogSlaStatus],
) -> pd.DataFrame:
    """Convert backlog SLA statuses to a stable dataframe."""
    return pd.DataFrame([status.model_dump() for status in statuses])


def governance_portfolio_summary_to_dataframe(
    summary: GovernancePortfolioSummary | None,
) -> pd.DataFrame:
    """Convert governance portfolio summary into a one-row dataframe."""
    if summary is None:
        return pd.DataFrame()
    return pd.DataFrame([summary.model_dump()])


def progress_snapshot_to_dataframe(
    snapshot: ProgressSnapshot | None,
) -> pd.DataFrame:
    """Convert a progress snapshot into a one-row dataframe."""
    if snapshot is None:
        return pd.DataFrame()
    return pd.DataFrame([snapshot.model_dump()])


def review_summary_to_dataframe(review_summary: ReviewSummary | None) -> pd.DataFrame:
    """Convert a review summary into a one-row dataframe."""
    if review_summary is None:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            {
                "accepted_count": review_summary.accepted_count,
                "rejected_count": review_summary.rejected_count,
                "edited_count": review_summary.edited_count,
                "manual_review_count": review_summary.manual_review_count,
                "total_reviewed_count": review_summary.total_reviewed_count,
            }
        ]
    )
