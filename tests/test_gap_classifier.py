"""Tests for governance gap classification."""

from app.core.governance.gap_classifier import GapClassifier
from app.core.models.ai_ready_score import AiReadyScore
from app.core.models.issue import Issue
from app.core.models.mapping_result import UnmappedField
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.rag_quality import RagQualityIssue
from app.core.models.text_to_sql_readiness import (
    TextToSqlReadinessIssue,
    TextToSqlReadinessScore,
)
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
    assert metadata_gaps[0].signal_count == 2
    assert metadata_gaps[0].affected_objects == [
        "customer_master.customer_id",
        "customer_master.customer_name",
    ]
    assert metadata_gaps[0].evidence_details["signal_counts"] == {
        "missing_field_cn_name": 1,
        "missing_field_description": 1,
    }
    assert "affected_objects=2" in str(metadata_gaps[0].reason)


def test_gap_classifier_includes_ai_ready_low_dimension_signals() -> None:
    result = WorkflowResult(
        ai_ready_scores=[
            AiReadyScore(
                object_type="table",
                object_name="sales_order",
                overall_score=58.0,
                ai_ready_level="C_govern_before_use",
                dimension_scores={
                    "understandability": 42.0,
                    "standardization": 55.0,
                    "security_controllability": 40.0,
                },
                summary="sales_order is not AI-ready enough.",
            )
        ]
    )

    gaps = GapClassifier().classify(result)
    by_type = {gap.gap_type: gap for gap in gaps}

    assert "metadata_completion_gap" in by_type
    assert "standard_mapping_gap" in by_type
    assert "ai_consumption_risk_gap" in by_type
    assert "ai_ready_low_understandability" in by_type["metadata_completion_gap"].source_signals
    assert "ai_ready_low_standardization" in by_type["standard_mapping_gap"].source_signals
    assert by_type["ai_consumption_risk_gap"].signal_count == 2
    assert by_type["ai_consumption_risk_gap"].severity == "high"


def test_gap_classifier_includes_rag_quality_and_text_to_sql_signals() -> None:
    result = WorkflowResult(
        rag_quality_issues=[
            RagQualityIssue(
                object_type="chunk",
                object_name="chunk_1021",
                issue_type="sensitive_chunk_public",
                severity="critical",
                evidence=["permission_label=public"],
                risk="Sensitive content may leak through retrieval.",
                suggestion="Move sensitive chunks to a restricted index.",
                category="permission_risk",
                requires_manual_review=True,
            )
        ],
        text_to_sql_readiness_scores=[
            TextToSqlReadinessScore(
                table_name="contract_info",
                readiness_score=58.0,
                readiness_level="govern_before_text_to_sql",
            )
        ],
        text_to_sql_readiness_issues=[
            TextToSqlReadinessIssue(
                table_name="contract_info",
                object_type="field",
                object_name="contract_info.status",
                issue_type="missing_enum_value_explanations",
                severity="high",
                dimension="enum_explainability",
                risk="The model may filter status with incorrect values.",
                suggestion="Add value-domain mappings.",
                requires_manual_review=True,
            )
        ],
    )

    gaps = GapClassifier().classify(result)

    rag_gap = next(
        gap for gap in gaps if gap.object_name == "chunk_1021"
    )
    text_to_sql_gaps = [
        gap for gap in gaps if gap.object_name == "contract_info"
    ]

    assert rag_gap.object_type == "chunk"
    assert rag_gap.gap_type == "ai_consumption_risk_gap"
    assert rag_gap.severity == "critical"
    assert rag_gap.source_signals == ["rag_quality_sensitive_chunk_public"]
    assert {gap.gap_type for gap in text_to_sql_gaps} == {
        "ai_consumption_risk_gap",
        "semantic_consistency_gap",
    }
    semantic_gap = next(
        gap for gap in text_to_sql_gaps if gap.gap_type == "semantic_consistency_gap"
    )
    assert semantic_gap.affected_objects == ["contract_info.status"]
