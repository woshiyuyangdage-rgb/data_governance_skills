"""Tests for AI-ready table scoring."""

from app.core.governance.ai_ready_assessor import AiReadyAssessor
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.execution_ready_rule import ExecutionReadyRule
from app.core.models.field_meta import FieldMeta
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult, UnmappedField
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.semantic_enrichment_result import (
    FieldDescriptionSuggestion,
    TableSemanticSummary,
)
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.workflow_engine import WorkflowEngine


def test_ai_ready_assessor_scores_evidence_rich_table_high() -> None:
    result = WorkflowResult(
        table_semantic_summaries=[
            TableSemanticSummary(
                table_name="contract_master",
                table_name_cn="Contract Master",
                original_description="Stores contract master data.",
                business_object="contract",
                business_purpose="record and manage contract master information",
                core_fields=["contract_id", "customer_id", "contract_amt"],
                applicable_scenarios=["contract lookup", "risk analysis"],
                ai_usage_risks=["no obvious AI consumption risk detected"],
                recommended_actions=[
                    "keep summary available for catalog, RAG, and Text-to-SQL context"
                ],
                generated_summary="Contract summary.",
                optimized_summary="Contract summary.",
                confidence=0.9,
                quality_tags=["table_description_usable"],
                requires_manual_review=False,
                business_domain="finance",
                key_concepts=["contract", "customer", "amount"],
                evidence=[
                    "table_name=contract_master",
                    "table_name_cn=Contract Master",
                    "table_description=Stores contract master data.",
                    "business_domain=finance",
                    "upstream_system=loan_core",
                    "downstream_applications=risk_dashboard",
                    "data_layer=dwd",
                    "primary_key_fields=contract_id",
                    "foreign_key_fields=customer_id",
                    "frequent_query_sql=available",
                ],
            )
        ],
        field_description_suggestions=[
            FieldDescriptionSuggestion(
                table_name="contract_master",
                field_name="contract_id",
                field_name_cn="Contract ID",
                original_description="Unique contract identifier",
                generated_description="Identifies the contract.",
                optimized_description="Unique contract identifier",
                confidence=0.9,
                evidence=["field_name=contract_id"],
                quality_tags=["description_usable"],
                governance_action="keep_current",
                requires_manual_review=False,
                business_domain="finance",
                standard_code="contract_id",
                standard_name="contract_id",
            ),
            FieldDescriptionSuggestion(
                table_name="contract_master",
                field_name="contract_amt",
                field_name_cn="Contract Amount",
                original_description="Contract amount",
                generated_description="Records the contract amount.",
                optimized_description="Contract amount",
                confidence=0.88,
                evidence=["field_name=contract_amt"],
                quality_tags=["description_usable"],
                governance_action="keep_current",
                requires_manual_review=False,
                business_domain="finance",
                standard_code="transaction_amount",
                standard_name="transaction_amount",
            ),
        ],
        mapping_results=[
            MappingResult(
                table_name="contract_master",
                field_name="contract_id",
                recommended_standard_code="contract_id",
                recommended_standard_name="contract_id",
                match_score=0.95,
                match_reason="exact match",
                candidate_count=1,
            )
        ],
        confirmed_mapping_results=[
            MappingResult(
                table_name="contract_master",
                field_name="contract_amt",
                recommended_standard_code="transaction_amount",
                recommended_standard_name="transaction_amount",
                match_score=0.92,
                match_reason="confirmed",
                candidate_count=1,
            )
        ],
        stg_field_suggestions=[
            StgFieldSuggestion(
                source_table_name="contract_master",
                source_field_name="contract_id",
                recommended_stg_field_name="contract_id",
                mapping_source="test",
                action="keep",
            )
        ],
        quality_rule_suggestions=[
            QualityRuleSuggestion(
                source_table_name="contract_master",
                source_field_name="contract_id",
                rule_type="not_null",
                rule_expression="not_null",
                severity="high",
                confidence=0.9,
                recommendation_source="test",
            )
        ],
        confirmed_quality_rules=[
            ConfirmedQualityRule(
                source_table_name="contract_master",
                source_field_name="contract_id",
                rule_type="not_null",
                rule_expression="not_null",
                severity="high",
                confirmation_source="test",
            )
        ],
        execution_ready_package=ExecutionReadyPackage(
            package_id="pkg-1",
            package_name="ai-ready-test",
            rule_count=1,
            rules=[
                ExecutionReadyRule(
                    rule_id="r1",
                    source_table_name="contract_master",
                    source_field_name="contract_id",
                    rule_type="not_null",
                    severity="high",
                )
            ],
        ),
    )

    scores = AiReadyAssessor().assess(result)

    table_score = next(score for score in scores if score.object_name == "contract_master")
    assert table_score.overall_score >= 80
    assert table_score.ai_ready_level in {"A_ai_ready", "B_basically_usable"}
    assert set(table_score.dimension_scores) == {
        "discoverability",
        "understandability",
        "semantic_consistency",
        "standardization",
        "quality_controllability",
        "security_controllability",
        "traceability",
        "ai_application_adaptability",
    }
    assert table_score.evidence


def test_ai_ready_assessor_flags_weak_table_for_governance() -> None:
    result = WorkflowResult(
        issues=[
            Issue(
                issue_id="i1",
                object_type="table",
                object_name="tmp_order_2022",
                issue_type="technical_object_defect",
                severity="medium",
                ai_risk="Technical table may pollute retrieval.",
            ),
            Issue(
                issue_id="i2",
                object_type="field",
                object_name="tmp_order_2022.cust_no",
                issue_type="missing_metadata_defect",
                severity="high",
                ai_risk="Models may not understand the exact field meaning.",
            ),
            Issue(
                issue_id="i3",
                object_type="field",
                object_name="tmp_order_2022.id_no",
                issue_type="sensitive_field_unlabeled",
                severity="high",
                ai_risk="Sensitive field could be surfaced without proper context.",
            ),
        ],
        unmapped_fields=[
            UnmappedField(
                table_name="tmp_order_2022",
                field_name="cust_no",
                reason="No confident standard mapping.",
            )
        ],
        table_semantic_summaries=[
            TableSemanticSummary(
                table_name="tmp_order_2022",
                generated_summary="Weak table summary.",
                optimized_summary="Weak table summary.",
                confidence=0.45,
                ai_usage_risks=["technical or lifecycle table may be selected incorrectly"],
                recommended_actions=["confirm lifecycle status before catalog exposure"],
                requires_manual_review=True,
            )
        ],
    )

    scores = AiReadyAssessor().assess(result)

    table_score = next(score for score in scores if score.object_name == "tmp_order_2022")
    assert table_score.ai_ready_level in {
        "C_govern_before_use",
        "D_not_recommended_for_ai",
    }
    assert table_score.dimension_scores["security_controllability"] < 80
    assert table_score.risk_flags
    assert table_score.recommended_actions


def test_workflow_readiness_assessment_attaches_ai_ready_scores() -> None:
    engine = WorkflowEngine()
    tables = [
        TableMeta(
            table_name="customer_master",
            table_name_cn="Customer Master",
            table_description="Stores customer master data.",
            system_name="crm",
            business_domain="customer",
            lifecycle_status="active",
            fields=[
                FieldMeta(
                    field_name="customer_id",
                    field_name_cn="Customer ID",
                    field_description="Unique customer identifier",
                    data_type="varchar",
                    standard_code="customer_id",
                    standard_name="customer_id",
                    is_primary_key=True,
                )
            ],
        )
    ]

    result = engine.run_governance_readiness_assessment(tables)

    assert result.ai_ready_scores
    assert result.ai_ready_summary["ai_ready_score_count"] == len(result.ai_ready_scores)
    assert "ai_ready_assessment_output" in result.skill_outputs
