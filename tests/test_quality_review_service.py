"""Tests for quality rule review and confirmed rule construction."""

from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.review.quality_override_store import build_quality_rule_key
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)


def _suggestion(field_name: str, rule_type: str) -> QualityRuleSuggestion:
    return QualityRuleSuggestion(
        source_table_name="sales_order",
        source_field_name=field_name,
        recommended_field_name=field_name,
        rule_type=rule_type,
        rule_expression=rule_type,
        severity="medium",
        priority="P2",
        recommendation_source="test",
        match_basis="unit_test",
        reason="test suggestion",
    )


def test_quality_review_actions_build_expected_confirmed_rules() -> None:
    suggestions = [
        _suggestion("order_id", "not_null"),
        _suggestion("status", "value_set"),
        _suggestion("legacy_code", "regex_format"),
        _suggestion("comment", "length_range"),
    ]
    records = build_quality_rule_review_records_from_results(
        suggestions,
        {
            "sales_order.order_id.not_null": {"review_action": "accept"},
            "sales_order.status.value_set": {
                "review_action": "edit",
                "final_rule_expression": "value in ('OPEN','CLOSED')",
                "final_severity": "high",
            },
            "sales_order.legacy_code.regex_format": {"review_action": "reject"},
            "sales_order.comment.length_range": {
                "review_action": "mark_for_manual_review"
            },
        },
        source="test",
    )

    reviewed_suggestions, applied_count, replay_summary = (
        apply_quality_rule_overrides_to_results(suggestions, records)
    )
    confirmed_rules = build_confirmed_quality_rules(suggestions, records)
    summary = summarize_quality_rule_review_records(
        records,
        confirmed_count=len(confirmed_rules),
    )

    assert applied_count == 4
    assert len(reviewed_suggestions) == 4
    assert replay_summary["confirmed_count"] == 2
    assert summary["accepted_count"] == 1
    assert summary["edited_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["manual_review_count"] == 1
    assert summary["confirmed_count"] == 2

    assert len(confirmed_rules) == 2
    edited_rule = next(rule for rule in confirmed_rules if rule.rule_type == "value_set")
    assert edited_rule.rule_expression == "value in ('OPEN','CLOSED')"
    assert edited_rule.severity == "high"
    assert edited_rule.confirmation_source == "override_edit"


def test_reject_and_manual_review_are_excluded_from_confirmed_rules() -> None:
    suggestions = [_suggestion("legacy_code", "regex_format")]
    records = build_quality_rule_review_records_from_results(
        suggestions,
        {
            "sales_order.legacy_code.regex_format": {
                "review_action": "mark_for_manual_review"
            }
        },
        source="test",
    )

    confirmed_rules = build_confirmed_quality_rules(suggestions, records)

    assert confirmed_rules == []


def test_cross_field_review_builds_confirmed_rule() -> None:
    suggestion = QualityRuleSuggestion(
        source_table_name="sales_order",
        source_field_name="start_date",
        rule_scope="cross_field",
        field_group=["start_date", "end_date"],
        rule_type="temporal_order",
        rule_expression="start_date <= end_date",
        severity="medium",
        priority="P2",
        confidence=1.0,
        review_priority="medium_review_priority",
        recommendation_source="cross_field_pattern",
        match_basis="start_date/end_date",
        reason="Start date should not be later than end date.",
    )
    key = build_quality_rule_key(
        suggestion.source_table_name,
        suggestion.source_field_name,
        suggestion.rule_type,
        rule_scope=suggestion.rule_scope,
        field_group=suggestion.field_group,
    )

    records = build_quality_rule_review_records_from_results(
        [suggestion],
        {key: {"review_action": "accept"}},
        source="test",
    )
    confirmed_rules = build_confirmed_quality_rules([suggestion], records)
    summary = summarize_quality_rule_review_records(
        records,
        confirmed_count=len(confirmed_rules),
    )

    assert len(confirmed_rules) == 1
    assert confirmed_rules[0].rule_scope == "cross_field"
    assert confirmed_rules[0].field_group == ["start_date", "end_date"]
    assert confirmed_rules[0].confidence == 1.0
    assert summary["cross_field_confirmed_count"] == 1


def test_cross_table_review_preserves_reference_metadata() -> None:
    suggestion = QualityRuleSuggestion(
        source_table_name="contract_info",
        source_field_name="customer_id",
        rule_name="contract_info.customer_id references customer_master.customer_id",
        rule_description="Recommended cross_table_reference quality check.",
        rule_scope="cross_table",
        field_group=["customer_id"],
        target_table_name="customer_master",
        target_field_name="customer_id",
        rule_type="cross_table_reference",
        rule_expression="contract_info.customer_id exists in customer_master.customer_id",
        severity="medium",
        priority="P2",
        risk_level="medium",
        confidence=0.8,
        requires_manual_review=True,
        review_priority="medium_review_priority",
        recommendation_source="cross_table_reference_pattern",
        match_basis="foreign_key=contract_info.customer_id; primary_key=customer_master.customer_id",
        reason="Foreign-key metadata indicates a parent table reference.",
        export_formats=["excel_quality_rule_list", "json_rule_package", "custom_sql_check"],
    )
    key = build_quality_rule_key(
        suggestion.source_table_name,
        suggestion.source_field_name,
        suggestion.rule_type,
        rule_scope=suggestion.rule_scope,
        field_group=suggestion.field_group,
    )

    records = build_quality_rule_review_records_from_results(
        [suggestion],
        {key: {"review_action": "accept"}},
        source="test",
    )
    confirmed_rules = build_confirmed_quality_rules([suggestion], records)

    assert records[0].target_table_name == "customer_master"
    assert records[0].export_formats == [
        "excel_quality_rule_list",
        "json_rule_package",
        "custom_sql_check",
    ]
    assert len(confirmed_rules) == 1
    confirmed = confirmed_rules[0]
    assert confirmed.rule_scope == "cross_table"
    assert confirmed.target_table_name == "customer_master"
    assert confirmed.target_field_name == "customer_id"
    assert confirmed.rule_name == suggestion.rule_name
    assert confirmed.export_formats == suggestion.export_formats
