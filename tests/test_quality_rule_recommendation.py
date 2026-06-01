"""Tests for rule-based quality rule recommendation."""

from app.core.models.field_meta import FieldMeta
from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta
from app.core.review import quality_override_store
from app.core.skills.data_quality_rule_skill import (
    QualityRuleRecommendationInput,
    QualityRuleRecommendationSkill,
)
from app.core.skills.data_quality_rule_skill import quality_rule_learning


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


def test_value_set_rule_uses_compact_sample_values() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="sales_order",
            fields=[
                FieldMeta(
                    field_name="order_status",
                    data_type="varchar",
                    sample_values="OPEN;CLOSED;CANCELLED;OPEN",
                )
            ],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    value_set_rule = next(
        rule
        for rule in result.quality_rule_suggestions
        if rule.rule_type == "value_set"
    )
    assert value_set_rule.rule_expression == "value in ('OPEN', 'CLOSED', 'CANCELLED')"
    assert "Derived accepted values from source sample_values count=3" in (
        value_set_rule.reason or ""
    )
    assert "value_set_size:3" in value_set_rule.learning_context


def test_value_set_rule_ignores_oversized_sample_values() -> None:
    skill = QualityRuleRecommendationSkill()
    sample_values = ";".join(f"S{index}" for index in range(20))
    tables = [
        TableMeta(
            table_name="sales_order",
            fields=[
                FieldMeta(
                    field_name="order_status",
                    data_type="varchar",
                    sample_values=sample_values,
                )
            ],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    value_set_rule = next(
        rule
        for rule in result.quality_rule_suggestions
        if rule.rule_type == "value_set"
    )
    assert value_set_rule.rule_expression == "value in predefined set"


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
    assert all(rule.rule_name for rule in result.quality_rule_suggestions)
    assert all(rule.rule_description for rule in result.quality_rule_suggestions)
    assert all(rule.risk_level for rule in result.quality_rule_suggestions)
    assert all(rule.export_formats for rule in result.quality_rule_suggestions)


def test_foreign_key_metadata_recommends_cross_table_reference_rule() -> None:
    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="customer_master",
            primary_key_fields=["customer_id"],
            fields=[
                FieldMeta(
                    field_name="customer_id",
                    data_type="varchar",
                    is_primary_key=True,
                )
            ],
        ),
        TableMeta(
            table_name="contract_info",
            foreign_key_fields=["customer_id"],
            fields=[
                FieldMeta(
                    field_name="contract_id",
                    data_type="varchar",
                    is_primary_key=True,
                ),
                FieldMeta(
                    field_name="customer_id",
                    data_type="varchar",
                    is_foreign_key=True,
                ),
            ],
        ),
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    reference_rules = [
        rule
        for rule in result.cross_field_quality_rules
        if rule.rule_scope == "cross_table"
        and rule.rule_type == "cross_table_reference"
    ]
    assert reference_rules
    rule = reference_rules[0]
    assert rule.source_table_name == "contract_info"
    assert rule.source_field_name == "customer_id"
    assert rule.target_table_name == "customer_master"
    assert rule.target_field_name == "customer_id"
    assert "contract_info.customer_id exists in customer_master.customer_id" == rule.rule_expression
    assert rule.requires_manual_review is True
    assert "custom_sql_check" in rule.export_formats
    assert "cross-table reference rules" in result.summary


def test_review_history_association_rules_promote_learned_rule(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_OVERRIDES_PATH",
        tmp_path / "quality_rule_overrides.csv",
    )
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_SESSIONS_DIR",
        tmp_path / "quality_rule_sessions",
    )
    quality_rule_learning.clear_quality_rule_learning_caches()

    records = [
        QualityRuleReviewRecord(
            source_table_name=f"trade_{index}",
            source_field_name=f"interest_rate_{index}",
            rule_type="numeric_range",
            original_rule_expression="value >= 0",
            final_rule_expression="value between 0 and 1",
            original_severity="medium",
            final_severity="medium",
            recommended_field_name=f"interest_rate_{index}",
            recommendation_source="source_field_fallback",
            match_basis=f"source_field_name=interest_rate_{index}",
            learning_context=["type:decimal", "token:rate", "source:source_field_fallback"],
            review_action="accept",
            reviewer_note="confirmed ratio/rate range",
            reviewed_at="2026-05-01T10:00:00",
            source="test",
        )
        for index in range(3)
    ]
    quality_override_store.save_quality_rule_review_records(records)

    skill = QualityRuleRecommendationSkill()
    tables = [
        TableMeta(
            table_name="trade_fact",
            fields=[FieldMeta(field_name="fee_rate", data_type="decimal")],
        )
    ]

    result = skill.run(QualityRuleRecommendationInput(tables=tables))

    assert result.quality_rule_suggestions
    first_rule = result.quality_rule_suggestions[0]
    assert first_rule.rule_type == "numeric_range"
    assert first_rule.review_priority == "learned_review_priority"
    assert first_rule.learned_confidence == 1.0
    assert first_rule.learned_support == 1.0
    assert first_rule.notes is not None
    assert "learned_from_quality_review_history" in first_rule.notes
