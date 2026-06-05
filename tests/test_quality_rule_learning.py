"""Tests for quality-rule association learning health."""

from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.skills.data_quality_rule_skill import quality_rule_learning
from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
    summarize_quality_rule_learning,
)


def _review_record(
    *,
    field_name: str,
    rule_type: str = "numeric_range",
    review_action: str = "accept",
) -> QualityRuleReviewRecord:
    return QualityRuleReviewRecord(
        source_table_name="trade_fact",
        source_field_name=field_name,
        rule_type=rule_type,
        review_action=review_action,
        learning_context=["type:decimal", "token:rate"],
        source="test",
    )


def test_quality_rule_learning_health_reports_active_state(monkeypatch) -> None:
    monkeypatch.setattr(
        quality_rule_learning,
        "quality_rule_learning_policy",
        lambda: {"enabled": True, "min_records": 3},
    )
    monkeypatch.setattr(quality_rule_learning, "fpgrowth", object())
    monkeypatch.setattr(quality_rule_learning, "association_rules", object())

    records = [
        _review_record(field_name="interest_rate"),
        _review_record(field_name="fee_rate"),
        _review_record(field_name="discount_rate"),
        _review_record(
            field_name="ignored_rate",
            review_action="reject",
        ),
    ]
    health = summarize_quality_rule_learning(
        records=records,
        associations=(
            {
                "antecedents": ("type:decimal", "token:rate"),
                "rule_type": "numeric_range",
                "support": 1.0,
                "confidence": 1.0,
                "lift": 1.0,
            },
        ),
    )

    assert health.status == "active"
    assert health.enabled is True
    assert health.dependency_available is True
    assert health.accepted_record_count == 3
    assert health.association_rule_count == 1
    assert health.learned_rule_types == ("numeric_range",)


def test_quality_rule_learning_health_reports_insufficient_records(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        quality_rule_learning,
        "quality_rule_learning_policy",
        lambda: {"enabled": True, "min_records": 3},
    )
    monkeypatch.setattr(quality_rule_learning, "fpgrowth", object())
    monkeypatch.setattr(quality_rule_learning, "association_rules", object())

    health = summarize_quality_rule_learning(
        records=[_review_record(field_name="interest_rate")],
        associations=(),
    )

    assert health.status == "insufficient_records"
    assert health.accepted_record_count == 1
    assert health.min_records == 3


def test_quality_rule_learning_health_reports_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        quality_rule_learning,
        "quality_rule_learning_policy",
        lambda: {"enabled": False, "min_records": 3},
    )

    health = summarize_quality_rule_learning(
        records=[_review_record(field_name="interest_rate")],
        associations=(),
    )

    assert health.status == "disabled"
    assert health.enabled is False
