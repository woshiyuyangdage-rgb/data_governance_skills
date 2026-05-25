"""Shared helpers for quality workflow runner mixins."""

from dataclasses import dataclass
from typing import Any

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.review.quality_batch_review_service import summarize_review_queue
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    summarize_quality_rule_review_records,
)
from app.core.skills.data_quality_rule_skill import QualityRuleRecommendationSkill


@dataclass(frozen=True)
class QualityReviewReplayArtifacts:
    """Review replay outputs derived from one quality recommendation set."""

    reviewed_quality_suggestions: list[QualityRuleSuggestion]
    confirmed_quality_rules: list[ConfirmedQualityRule]
    quality_review_summary: dict[str, object]
    quality_review_queue_summary: dict[str, object]
    applied_quality_count: int
    field_reviewed_quality_suggestions: list[QualityRuleSuggestion]


def build_quality_reviewable_rules(
    quality_output: Any,
) -> list[QualityRuleSuggestion]:
    """Expand a quality recommendation output into reviewable suggestions."""
    reviewable_rules = list(quality_output.quality_rule_suggestions)
    reviewable_rules.extend(
        QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
        for rule in quality_output.cross_field_quality_rules
    )
    return reviewable_rules


def build_quality_review_queue_summary(
    quality_output: Any,
) -> dict[str, object]:
    """Summarize the queue derived from one quality recommendation output."""
    return summarize_review_queue(build_quality_reviewable_rules(quality_output))


def build_quality_review_replay_artifacts(
    reviewable_quality_rules: list[QualityRuleSuggestion],
) -> QualityReviewReplayArtifacts:
    """Apply saved quality review overrides and collect replay artifacts."""
    quality_overrides = load_quality_rule_overrides()
    reviewed_quality_suggestions, applied_quality_count, _ = (
        apply_quality_rule_overrides_to_results(
            reviewable_quality_rules,
            quality_overrides,
        )
    )
    confirmed_quality_rules = build_confirmed_quality_rules(
        reviewable_quality_rules,
        quality_overrides,
    )
    quality_review_summary = summarize_quality_rule_review_records(
        quality_overrides,
        confirmed_count=len(confirmed_quality_rules),
    )
    quality_review_queue_summary = summarize_review_queue(
        reviewed_quality_suggestions
    )
    field_reviewed_quality_suggestions = [
        rule for rule in reviewed_quality_suggestions if rule.rule_scope == "field"
    ]
    return QualityReviewReplayArtifacts(
        reviewed_quality_suggestions=reviewed_quality_suggestions,
        confirmed_quality_rules=confirmed_quality_rules,
        quality_review_summary=quality_review_summary,
        quality_review_queue_summary=quality_review_queue_summary,
        applied_quality_count=applied_quality_count,
        field_reviewed_quality_suggestions=field_reviewed_quality_suggestions,
    )


def append_quality_message(
    message: str,
    status: str,
    tables: list[object],
    suffix: str,
) -> str:
    """Append one success-only suffix to a workflow message."""
    if tables and status == "success":
        return f"{message}{suffix}"
    return message


def build_quality_workflow_result_kwargs(
    base_result: Any,
    quality_output: Any,
    *,
    quality_rule_suggestions: list[QualityRuleSuggestion],
    skill_outputs: dict[str, Any],
    message: str,
    status: str | None = None,
    confirmed_quality_rules: list[ConfirmedQualityRule] | None = None,
    quality_rule_review_summary: dict[str, object] | None = None,
    quality_review_queue_summary: dict[str, object] | None = None,
    review_summary: Any = None,
) -> dict[str, Any]:
    """Build the common WorkflowResult payload for quality runner variants."""
    return {
        "input_table_count": base_result.input_table_count,
        "issue_count": base_result.issue_count + len(quality_output.issues),
        "task_count": base_result.task_count,
        "issues": base_result.issues + quality_output.issues,
        "tasks": base_result.tasks,
        "field_description_suggestions": base_result.field_description_suggestions,
        "table_semantic_summaries": base_result.table_semantic_summaries,
        "semantic_enrichment_summary": base_result.semantic_enrichment_summary,
        "mapping_results": base_result.mapping_results,
        "confirmed_mapping_results": base_result.confirmed_mapping_results,
        "unmapped_fields": base_result.unmapped_fields,
        "mapping_summary": base_result.mapping_summary,
        "stg_suggestions": base_result.stg_suggestions,
        "stg_field_suggestions": base_result.stg_field_suggestions,
        "confirmed_stg_suggestions": base_result.confirmed_stg_suggestions,
        "stg_summary": base_result.stg_summary,
        "quality_rule_suggestions": quality_rule_suggestions,
        "cross_field_quality_rules": quality_output.cross_field_quality_rules,
        "quality_rule_packages": quality_output.quality_rule_packages,
        "quality_rule_summary": quality_output.summary,
        "confirmed_quality_rules": confirmed_quality_rules or [],
        "quality_rule_review_summary": quality_rule_review_summary or {},
        "quality_review_queue_summary": quality_review_queue_summary or {},
        "review_summary": review_summary,
        "skill_outputs": skill_outputs,
        "status": status or base_result.status,
        "message": message,
    }
