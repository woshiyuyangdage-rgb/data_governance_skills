"""Tests for governance gap classification."""

from app.core.governance.gap_classifier import GapClassifier
from app.core.models.issue import Issue
from app.core.models.mapping_result import UnmappedField
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.workflow_result import WorkflowResult


def test_gap_classifier_maps_issues_and_review_signals_to_gaps() -> None:
    result = WorkflowResult(
        issues=[
            Issue(
                issue_id="i1",
                object_type="field",
                object_name="sales_order.order_id",
                issue_type="missing_field_description",
                severity="low",
                suggestion="Add business description.",
            )
        ],
        unmapped_fields=[
            UnmappedField(
                table_name="sales_order",
                field_name="order_channel",
                best_candidate_score=0.3,
                reason="Low mapping score.",
            )
        ],
        quality_rule_suggestions=[
            QualityRuleSuggestion(
                source_table_name="sales_order",
                source_field_name="order_channel",
                rule_type="value_set",
                rule_expression="value in accepted set",
                severity="medium",
                confidence=0.4,
                review_priority="high_review_priority",
                recommendation_source="test",
            )
        ],
        quality_review_queue_summary={"low_confidence_rule_count": 1},
    )

    gaps = GapClassifier().classify(result)
    gap_types = {gap.gap_type for gap in gaps}

    assert "metadata_completion_gap" in gap_types
    assert "standard_mapping_gap" in gap_types
    assert "quality_rule_gap" in gap_types
    assert "review_backlog_gap" in gap_types
    assert any(gap.object_name == "sales_order" for gap in gaps)


def test_gap_classifier_aggregates_same_gap_type_by_table() -> None:
    result = WorkflowResult(
        issues=[
            Issue(
                issue_id="i1",
                object_type="field",
                object_name="customer_master.customer_id",
                issue_type="missing_field_description",
                severity="low",
            ),
            Issue(
                issue_id="i2",
                object_type="field",
                object_name="customer_master.customer_name",
                issue_type="missing_field_cn_name",
                severity="medium",
            ),
        ]
    )

    gaps = GapClassifier().classify(result)

    metadata_gaps = [
        gap for gap in gaps if gap.gap_type == "metadata_completion_gap"
    ]
    assert len(metadata_gaps) == 1
    assert metadata_gaps[0].severity == "medium"
    assert set(metadata_gaps[0].source_signals) == {
        "missing_field_description",
        "missing_field_cn_name",
    }

