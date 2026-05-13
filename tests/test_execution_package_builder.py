"""Tests for execution-ready package builder."""

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule


def _confirmed_rules() -> list[ConfirmedQualityRule]:
    return [
        ConfirmedQualityRule(
            source_table_name="sales_order",
            source_field_name="order_id",
            recommended_field_name="order_id",
            rule_type="not_null",
            rule_expression="not_null",
            severity="high",
            priority=None,
            confirmation_source="override_accept",
            match_basis="identifier",
            reason="identifier completeness",
        )
    ]


def test_confirmed_rules_can_build_execution_ready_package() -> None:
    builder = ExecutionPackageBuilder()

    package = builder.build_package(_confirmed_rules(), profile_name="test_profile")

    assert package.package_id.startswith("exec_pkg_")
    assert package.rule_count == 1
    assert package.rules[0].rule_id.startswith("rule_")
    assert package.rules[0].semantic_type == "completeness"
    assert package.rules[0].execution_mode == "batch_validation"
    assert package.rules[0].priority == "P1"
    assert package.rules[0].engine_hints["dbt"] == "not_null"
    assert package.summary is not None


def test_package_summary_is_report_friendly() -> None:
    builder = ExecutionPackageBuilder()
    package = builder.build_package(_confirmed_rules(), profile_name="test_profile")

    summary = builder.summarize_package(package)

    assert summary["package_id"] == package.package_id
    assert summary["rule_count"] == 1
    assert summary["semantic_type_counts"]["completeness"] == 1
    assert summary["execution_mode_counts"]["batch_validation"] == 1


def test_cross_field_confirmed_rule_enters_execution_package() -> None:
    builder = ExecutionPackageBuilder()
    rules = _confirmed_rules() + [
        ConfirmedQualityRule(
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
            confirmation_source="override_accept",
            match_basis="start_date/end_date",
            reason="Start date should not be later than end date.",
        )
    ]

    package = builder.build_package(rules, profile_name="test_profile")
    summary = builder.summarize_package(package)
    cross_rule = next(rule for rule in package.rules if rule.rule_scope == "cross_field")

    assert summary["field_rule_count"] == 1
    assert summary["cross_field_rule_count"] == 1
    assert cross_rule.field_group == ["start_date", "end_date"]
    assert cross_rule.execution_expression == "start_date <= end_date"
    assert cross_rule.engine_hints["custom_only"] is True
