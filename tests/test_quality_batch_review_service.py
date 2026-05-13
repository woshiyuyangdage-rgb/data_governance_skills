"""Tests for batch quality rule review helpers."""

from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.review.quality_batch_review_service import (
    bulk_accept_by_rule_type,
    bulk_accept_by_table,
    bulk_mark_manual_review_by_low_confidence,
    summarize_review_queue,
)


def _suggestion(
    table: str,
    field: str,
    rule_type: str,
    confidence: float,
    rule_scope: str = "field",
) -> QualityRuleSuggestion:
    field_group = [field, "end_date"] if rule_scope == "cross_field" else []
    return QualityRuleSuggestion(
        source_table_name=table,
        source_field_name=field,
        rule_scope=rule_scope,
        field_group=field_group,
        rule_type=rule_type,
        rule_expression=rule_type,
        severity="medium",
        priority="P2",
        confidence=confidence,
        review_priority=(
            "high_review_priority"
            if confidence <= 0.4
            else "medium_review_priority"
        ),
        recommendation_source="test",
    )


def test_bulk_accept_by_rule_type_selects_matching_rules() -> None:
    suggestions = [
        _suggestion("sales_order", "order_id", "not_null", 1.0),
        _suggestion("sales_order", "status", "value_set", 0.8),
    ]

    records = bulk_accept_by_rule_type(suggestions, "not_null")

    assert len(records) == 1
    assert records[0].review_action == "accept"
    assert records[0].rule_type == "not_null"


def test_bulk_accept_by_table_selects_field_and_cross_field_rules() -> None:
    suggestions = [
        _suggestion("sales_order", "order_id", "not_null", 1.0),
        _suggestion("sales_order", "start_date", "temporal_order", 1.0, "cross_field"),
        _suggestion("customer", "customer_id", "not_null", 1.0),
    ]

    records = bulk_accept_by_table(suggestions, "sales_order")

    assert len(records) == 2
    assert {record.rule_scope for record in records} == {"field", "cross_field"}


def test_low_confidence_rules_are_marked_for_manual_review() -> None:
    suggestions = [
        _suggestion("sales_order", "order_id", "not_null", 1.0),
        _suggestion("sales_order", "legacy_code", "reference_consistency_hint", 0.4),
    ]

    records = bulk_mark_manual_review_by_low_confidence(suggestions, threshold=0.4)
    summary = summarize_review_queue(suggestions)

    assert len(records) == 1
    assert records[0].review_action == "mark_for_manual_review"
    assert summary["low_confidence_rule_count"] == 1
