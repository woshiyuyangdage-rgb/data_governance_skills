"""Tests for governance readiness scoring."""

from app.core.governance.readiness_assessor import ReadinessAssessor
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.issue import Issue
from app.core.models.mapping_result import UnmappedField
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.workflow_result import WorkflowResult


def test_readiness_assessor_builds_table_and_overall_scores() -> None:
    result = WorkflowResult(
        issues=[
            Issue(
                issue_id="i1",
                object_type="table",
                object_name="customer_master",
                issue_type="missing_table_description",
                severity="medium",
                suggestion="Complete table description.",
            )
        ],
        unmapped_fields=[
            UnmappedField(
                table_name="customer_master",
                field_name="customer_status",
                reason="No confident standard mapping.",
            )
        ],
        quality_rule_suggestions=[
            QualityRuleSuggestion(
                source_table_name="customer_master",
                source_field_name="customer_id",
                rule_type="not_null",
                rule_expression="not_null",
                severity="high",
                confidence=0.4,
                review_priority="high_review_priority",
                recommendation_source="test",
            )
        ],
        confirmed_quality_rules=[
            ConfirmedQualityRule(
                source_table_name="customer_master",
                source_field_name="customer_id",
                rule_type="not_null",
                rule_expression="not_null",
                severity="high",
                confirmation_source="override_accept",
            )
        ],
        quality_review_queue_summary={"low_confidence_rule_count": 1},
    )

    scores = ReadinessAssessor().assess(result)

    table_score = next(score for score in scores if score.object_name == "customer_master")
    overall = next(score for score in scores if score.object_type == "overall")
    assert table_score.overall_score < 1.0
    assert table_score.readiness_level in {"ready", "partially_ready", "not_ready"}
    assert "metadata_readiness" in table_score.dimension_scores
    assert overall.object_name == "overall"


def test_readiness_level_thresholds_are_applied() -> None:
    assessor = ReadinessAssessor(
        policies={
            "dimensions": {},
            "thresholds": {"ready": 0.8, "partially_ready": 0.5},
            "scoring_rules": {},
        }
    )

    assert assessor.infer_readiness_level(0.9) == "ready"
    assert assessor.infer_readiness_level(0.6) == "partially_ready"
    assert assessor.infer_readiness_level(0.4) == "not_ready"

