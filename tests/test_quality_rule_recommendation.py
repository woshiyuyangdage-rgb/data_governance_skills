"""Tests for rule-based quality rule recommendation."""

from app.core.models.field_meta import FieldMeta
from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta
from app.core.skills.data_quality_rule_skill import (
    QualityRuleRecommendationInput,
    QualityRuleRecommendationSkill,
)


def test_identifier_field_recommends_not_null_and_uniqueness() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="customer_master",
            fields=[FieldMeta(field_name="cust_id", data_type="varchar")],
        )
    ]
    confirmed_mapping_results = [
        MappingResult(
            table_name="customer_master",
            field_name="cust_id",
            recommended_standard_code="customer_id",
            recommended_standard_name="customer_id",
            match_score=1.0,
            match_reason="test",
            candidate_count=1,
        )
    ]

    result = skill.run(
        QualityRuleRecommendationInput(
            tables=tables,
            confirmed_mapping_results=confirmed_mapping_results,
        )
    )

    rule_types = {
        item.rule_type
        for item in result.quality_rule_suggestions
        if item.source_field_name == "cust_id"
    }
    assert "not_null" in rule_types
    assert "uniqueness" in rule_types


def test_amount_field_recommends_numeric_range() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="sales_order",
            fields=[FieldMeta(field_name="order_amt", data_type="decimal")],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    assert any(
        item.rule_type == "numeric_range"
        for item in result.quality_rule_suggestions
    )


def test_date_field_recommends_date_format() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="snapshot_table",
            fields=[FieldMeta(field_name="snapshot_dt", data_type="date")],
        )
    ]
    stg_suggestions = [
        StgFieldSuggestion(
            source_table_name="snapshot_table",
            source_field_name="snapshot_dt",
            recommended_stg_field_name="snapshot_date",
            recommended_data_type="date",
            mapping_source="naming_enhancement",
            action="rename",
        )
    ]

    result = skill.run(
        QualityRuleRecommendationInput(
            tables=tables,
            stg_suggestions=stg_suggestions,
        )
    )

    assert any(
        item.rule_type == "date_format"
        for item in result.quality_rule_suggestions
    )


def test_mapping_priority_wins_over_source_fallback() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="customer_master",
            fields=[FieldMeta(field_name="customer_id", data_type="varchar")],
        )
    ]
    mapping_results = [
        MappingResult(
            table_name="customer_master",
            field_name="customer_id",
            recommended_standard_code="customer_id",
            recommended_standard_name="customer_id",
            match_score=0.92,
            match_reason="test",
            candidate_count=1,
        )
    ]

    result = skill.run(
        QualityRuleRecommendationInput(
            tables=tables,
            mapping_results=mapping_results,
        )
    )

    assert result.quality_rule_suggestions
    assert all(
        item.recommendation_source == "standard_mapping"
        for item in result.quality_rule_suggestions
    )


def test_deduplication_keeps_unique_rule_types() -> None:
    suggestions = [
        QualityRuleSuggestion(
            source_table_name="t1",
            source_field_name="customer_id",
            rule_type="not_null",
            severity="high",
            recommendation_source="standard_mapping",
        ),
        QualityRuleSuggestion(
            source_table_name="t1",
            source_field_name="customer_id",
            rule_type="not_null",
            severity="high",
            recommendation_source="standard_mapping",
        ),
    ]

    deduped = QualityRuleRecommendationSkill.deduplicate_rules_for_field(suggestions)

    assert len(deduped) == 1


def test_start_end_fields_recommend_temporal_order() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="order_lifecycle",
            fields=[
                FieldMeta(field_name="start_date", data_type="date"),
                FieldMeta(field_name="end_date", data_type="date"),
            ],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    temporal_rules = [
        rule
        for rule in result.cross_field_quality_rules
        if rule.rule_type == "temporal_order"
        and {"start_date", "end_date"}.issubset(set(rule.field_group))
    ]
    assert temporal_rules
    assert temporal_rules[0].confidence is not None
    assert temporal_rules[0].review_priority == "medium_review_priority"


def test_amount_currency_fields_recommend_paired_presence() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="sales_order",
            fields=[
                FieldMeta(field_name="amount", data_type="decimal"),
                FieldMeta(field_name="currency", data_type="varchar"),
            ],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    assert any(
        rule.rule_type == "paired_presence"
        and {"amount", "currency"}.issubset(set(rule.field_group))
        and rule.confidence is not None
        and rule.review_priority == "medium_review_priority"
        for rule in result.cross_field_quality_rules
    )


def test_status_code_name_fields_recommend_paired_presence() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="status_reference",
            fields=[
                FieldMeta(field_name="status_code", data_type="varchar"),
                FieldMeta(field_name="status_name", data_type="varchar"),
            ],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    assert any(
        rule.rule_type == "paired_presence"
        and {"status_code", "status_name"}.issubset(set(rule.field_group))
        for rule in result.cross_field_quality_rules
    )


def test_field_level_rules_include_confidence_and_review_priority() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="customer_master",
            fields=[FieldMeta(field_name="customer_id", data_type="varchar")],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    assert result.quality_rule_suggestions
    assert all(rule.confidence is not None for rule in result.quality_rule_suggestions)
    assert all(rule.review_priority is not None for rule in result.quality_rule_suggestions)
