"""Tests for local Text-to-SQL metadata readiness assessment."""

from app.core.governance.text_to_sql_readiness_assessor import (
    TextToSqlReadinessAssessor,
)
from app.core.models.field_meta import FieldMeta
from app.core.models.text_to_sql_readiness import (
    TextToSqlMetricDefinition,
    TextToSqlQueryExample,
    TextToSqlTableMetadata,
    TextToSqlTableRelationship,
)


def test_text_to_sql_readiness_assessor_scores_rich_metadata_high() -> None:
    result = TextToSqlReadinessAssessor().assess(
        [
            TextToSqlTableMetadata(
                table_name="contract_info",
                table_name_cn="Contract Info",
                table_description="Stores financing contract master information and lifecycle status.",
                business_domain="finance",
                permission_label="internal",
                sensitivity_label="internal",
                primary_key_fields=["contract_id"],
                foreign_key_fields=["customer_id"],
                fields=[
                    FieldMeta(
                        field_name="contract_id",
                        field_name_cn="Contract ID",
                        field_description="Unique contract identifier.",
                        data_type="varchar",
                        is_primary_key=True,
                    ),
                    FieldMeta(
                        field_name="customer_id",
                        field_name_cn="Customer ID",
                        field_description="Customer identifier used to join customer master data.",
                        data_type="varchar",
                        is_foreign_key=True,
                    ),
                    FieldMeta(
                        field_name="contract_status",
                        field_name_cn="Contract Status",
                        field_description="Lifecycle status of the financing contract.",
                        data_type="varchar",
                    ),
                    FieldMeta(
                        field_name="contract_amt",
                        field_name_cn="Contract Amount",
                        field_description="Approved contract amount in CNY.",
                        data_type="decimal",
                    ),
                ],
                relationships=[
                    TextToSqlTableRelationship(
                        source_table="contract_info",
                        source_field="customer_id",
                        target_table="customer_master",
                        target_field="customer_id",
                        relationship_type="many_to_one",
                    )
                ],
                metric_definitions=[
                    TextToSqlMetricDefinition(
                        metric_name="contract_amount",
                        description="Sum of contract amount.",
                        filters="contract_status = 'active'",
                        time_grain="month",
                        status_scope="active contracts",
                        unit="CNY",
                    )
                ],
                enum_definitions={
                    "contract_status": {
                        "active": "Active contract",
                        "closed": "Closed contract",
                    }
                },
                sample_sql=[
                    TextToSqlQueryExample(
                        question="How many active contracts are there?",
                        sql="select count(*) from contract_info where contract_status = 'active'",
                        business_explanation="Counts active contract records.",
                    )
                ],
            )
        ]
    )

    assert result.issue_count == 0
    assert result.scores[0].readiness_score >= 80
    assert result.scores[0].readiness_level in {
        "ready_for_text_to_sql",
        "usable_after_minor_metadata_completion",
    }
    assert set(result.scores[0].dimension_scores) == {
        "table_identifiability",
        "field_understandability",
        "relationship_inferability",
        "metric_clarity",
        "enum_explainability",
        "security_permission_fit",
        "query_example_support",
    }


def test_text_to_sql_readiness_assessor_flags_weak_metadata() -> None:
    result = TextToSqlReadinessAssessor().assess(
        [
            TextToSqlTableMetadata(
                table_name="tmp_order_log",
                table_description="tmp",
                lifecycle_status="temporary",
                similar_table_names=["order_info", "order_detail"],
                fields=[
                    FieldMeta(field_name="id", field_description="id"),
                    FieldMeta(field_name="status", field_description="status"),
                    FieldMeta(field_name="amt", field_description="amount"),
                    FieldMeta(field_name="phone", field_description="phone"),
                ],
            )
        ]
    )

    issue_types = {issue.issue_type for issue in result.issues}
    assert "weak_table_description" in issue_types
    assert "technical_or_lifecycle_table" in issue_types
    assert "weak_field_descriptions" in issue_types
    assert "missing_join_signals" in issue_types
    assert "missing_metric_definitions" in issue_types
    assert "missing_enum_value_explanations" in issue_types
    assert "missing_permission_label" in issue_types
    assert result.scores[0].readiness_level in {
        "govern_before_text_to_sql",
        "not_recommended",
    }
    assert result.summary["issue_count"] == result.issue_count
