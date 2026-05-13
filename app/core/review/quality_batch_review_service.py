"""Batch review helpers for quality rule review workbench."""

from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.review.quality_override_store import build_quality_rule_key
from app.core.review.quality_review_service import (
    build_quality_rule_review_records_from_results,
)


def _rule_key(rule: QualityRuleSuggestion) -> str:
    return build_quality_rule_key(
        rule.source_table_name,
        rule.source_field_name,
        rule.rule_type,
        rule_scope=rule.rule_scope,
        field_group=rule.field_group,
    )


def _selected_records(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    selected_keys: set[str],
    action: str,
    source: str,
    reviewer_note: str | None = None,
) -> list[QualityRuleReviewRecord]:
    review_inputs = {}
    selected_rules: list[QualityRuleSuggestion] = []
    for rule in quality_rule_suggestions:
        key = _rule_key(rule)
        if key not in selected_keys:
            continue
        selected_rules.append(rule)
        review_inputs[key] = {
            "review_action": action,
            "final_rule_expression": rule.rule_expression,
            "final_severity": rule.severity,
            "reviewer_note": reviewer_note,
        }
    return build_quality_rule_review_records_from_results(
        selected_rules,
        review_inputs,
        source=source,
    )


def bulk_accept_by_rule_type(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    rule_type: str,
    source: str = "batch_review",
) -> list[QualityRuleReviewRecord]:
    """Build accept records for all suggestions of one rule type."""
    normalized_type = str(rule_type).strip().lower()
    selected = {
        _rule_key(rule)
        for rule in quality_rule_suggestions
        if rule.rule_type.strip().lower() == normalized_type
    }
    return _selected_records(
        quality_rule_suggestions,
        selected,
        "accept",
        source,
        reviewer_note=f"Batch accepted rule_type={normalized_type}.",
    )


def bulk_accept_by_table(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    table_name: str,
    source: str = "batch_review",
) -> list[QualityRuleReviewRecord]:
    """Build accept records for all suggestions from one source table."""
    normalized_table = str(table_name).strip().lower()
    selected = {
        _rule_key(rule)
        for rule in quality_rule_suggestions
        if rule.source_table_name.strip().lower() == normalized_table
    }
    return _selected_records(
        quality_rule_suggestions,
        selected,
        "accept",
        source,
        reviewer_note=f"Batch accepted table={normalized_table}.",
    )


def bulk_mark_manual_review_by_low_confidence(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    threshold: float = 0.4,
    source: str = "batch_review",
) -> list[QualityRuleReviewRecord]:
    """Build manual-review records for low-confidence suggestions."""
    selected = {
        _rule_key(rule)
        for rule in quality_rule_suggestions
        if rule.confidence is not None and rule.confidence <= threshold
    }
    return _selected_records(
        quality_rule_suggestions,
        selected,
        "mark_for_manual_review",
        source,
        reviewer_note=f"Batch marked confidence <= {threshold} for manual review.",
    )


def summarize_review_queue(
    quality_rule_suggestions: list[QualityRuleSuggestion],
) -> dict[str, object]:
    """Summarize a review queue by scope, priority, and confidence."""
    priority_counts: dict[str, int] = {}
    scope_counts: dict[str, int] = {}
    low_confidence_count = 0
    for rule in quality_rule_suggestions:
        priority = rule.review_priority or "unspecified"
        scope = rule.rule_scope or "field"
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        scope_counts[scope] = scope_counts.get(scope, 0) + 1
        if rule.confidence is not None and rule.confidence <= 0.4:
            low_confidence_count += 1
    return {
        "total_rule_count": len(quality_rule_suggestions),
        "field_rule_count": scope_counts.get("field", 0),
        "cross_field_rule_count": scope_counts.get("cross_field", 0),
        "low_confidence_rule_count": low_confidence_count,
        "review_priority_counts": priority_counts,
        "rule_scope_counts": scope_counts,
    }


# TODO: extend batch review with domain-specific policies once governance packs become domain-owned assets.
