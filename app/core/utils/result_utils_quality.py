"""Quality, review, and execution-package dataframe helpers."""

import pandas as pd

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.rule_export_result import RuleExportResult


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

