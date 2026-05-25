"""Tests for evidence-based semantic enrichment."""

from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta
from app.core.skills.metadata_diagnosis_skill import (
    MetadataSemanticEnrichmentInput,
    MetadataSemanticEnrichmentSkill,
)


def test_field_description_generation_uses_evidence_and_can_auto_complete() -> None:
    skill = MetadataSemanticEnrichmentSkill()
    tables = [
        TableMeta(
            table_name="finance_contract",
            table_name_cn="Finance Contract",
            table_description="Stores finance contract master records.",
            business_domain="finance",
            fields=[
                FieldMeta(
                    field_name="contract_amt",
                    field_name_cn="Contract Amount",
                    data_type="decimal",
                    data_length="18,2",
                    sample_values="100.00;200.00",
                    standard_code="transaction_amount",
                    standard_name="transaction_amount",
                    business_domain="finance",
                )
            ],
        )
    ]

    result = skill.run(MetadataSemanticEnrichmentInput(tables=tables))

    suggestion = result.field_description_suggestions[0]
    assert suggestion.confidence >= 0.78
    assert suggestion.requires_manual_review is False
    assert suggestion.governance_action == "auto_complete"
    assert "Records" in suggestion.generated_description
    assert "data_type=decimal" in suggestion.evidence
    assert "standard=transaction_amount" in suggestion.evidence


def test_field_description_generation_marks_weak_context_for_manual_review() -> None:
    skill = MetadataSemanticEnrichmentSkill()
    tables = [
        TableMeta(
            table_name="tmp_table",
            fields=[
                FieldMeta(
                    field_name="amt",
                    field_description="金额",
                    data_type="decimal",
                )
            ],
        )
    ]

    result = skill.run(MetadataSemanticEnrichmentInput(tables=tables))

    suggestion = result.field_description_suggestions[0]
    assert suggestion.confidence <= 0.55
    assert suggestion.requires_manual_review is True
    assert suggestion.governance_action == "manual_review"
    assert "description_needs_manual_confirmation" in suggestion.quality_tags


def test_table_semantic_summary_uses_field_concepts() -> None:
    skill = MetadataSemanticEnrichmentSkill()
    tables = [
        TableMeta(
            table_name="fin_contract_info",
            table_name_cn="Finance Contract Info",
            table_description="Stores finance contract master records.",
            system_name="loan_core",
            business_domain="finance",
            data_layer="dwd",
            downstream_applications=["risk_dashboard"],
            usage_scenarios="contract lookup; risk analysis",
            primary_key_fields=["contract_id"],
            fields=[
                FieldMeta(
                    field_name="contract_id",
                    field_name_cn="Contract ID",
                    field_description="Unique contract identifier",
                    is_primary_key=True,
                ),
                FieldMeta(
                    field_name="customer_id",
                    field_name_cn="Customer ID",
                    field_description="Customer identifier",
                    is_foreign_key=True,
                ),
                FieldMeta(
                    field_name="contract_amt",
                    field_name_cn="Contract Amount",
                    field_description="Contract amount",
                    data_type="decimal",
                ),
                FieldMeta(
                    field_name="contract_status",
                    field_name_cn="Contract Status",
                    field_description="Contract status",
                ),
                FieldMeta(
                    field_name="start_date",
                    field_name_cn="Start Date",
                    field_description="Contract start date",
                    data_type="date",
                ),
            ],
        )
    ]

    result = skill.run(MetadataSemanticEnrichmentInput(tables=tables))

    summary = result.table_semantic_summaries[0]
    assert summary.confidence >= 0.7
    assert summary.business_object == "contract"
    assert "contract" in summary.business_purpose
    assert "Contract ID" in summary.core_fields
    assert "risk analysis" in summary.applicable_scenarios
    assert any(
        "status" in risk or "amount" in risk
        for risk in summary.ai_usage_risks
    )
    assert summary.recommended_actions
    assert "Core fields include" in summary.generated_summary
    assert "upstream_system=loan_core" in summary.evidence
