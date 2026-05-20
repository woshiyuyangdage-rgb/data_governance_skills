"""Tests for the P1.5 STG structure suggestion skill."""

from app.core.models.field_meta import FieldMeta
from app.core.models.mapping_result import MappingResult
from app.core.models.stg_review_record import StgReviewRecord
from app.core.models.table_meta import TableMeta
from app.core.skills.stg_standardization_skill import (
    StgStructureSuggestionInput,
    StgStructureSuggestionSkill,
)


def test_stg_structure_skill_generates_table_and_field_suggestions() -> None:
    skill = StgStructureSuggestionSkill()
    tables = [
        TableMeta(
            table_name="ods_customer_snapshot",
            table_name_cn="customer snapshot",
            fields=[
                FieldMeta(
                    field_name="customer_id",
                    field_name_cn="customer id",
                    data_type="varchar",
                    nullable=False,
                ),
                FieldMeta(
                    field_name="snapshot_dt",
                    field_name_cn="snapshot date",
                    data_type="date",
                    nullable=False,
                ),
                FieldMeta(
                    field_name="batch_no",
                    field_name_cn="batch number",
                    data_type="bigint",
                    nullable=False,
                ),
            ],
        )
    ]
    mapping_results = [
        MappingResult(
            table_name="ods_customer_snapshot",
            field_name="customer_id",
            recommended_standard_code="customer_id",
            recommended_standard_name="customer_id",
            recommended_standard_name_cn="customer id",
            match_score=1.0,
            match_reason="exact match",
            candidate_count=1,
        )
    ]

    result = skill.run(
        StgStructureSuggestionInput(
            tables=tables,
            mapping_results=mapping_results,
            naming_field_suggestions={
                "ods_customer_snapshot.snapshot_dt": "snapshot_date",
            },
        )
    )

    assert result.stg_table_suggestions
    assert result.field_suggestions_flat

    table_suggestion = result.stg_table_suggestions[0]
    assert table_suggestion.recommended_stg_table_name == "stg_customer_snapshot"

    field_lookup = {
        suggestion.source_field_name: suggestion for suggestion in result.field_suggestions_flat
    }
    assert field_lookup["customer_id"].mapping_source == "standard_mapping"
    assert field_lookup["customer_id"].recommended_stg_field_name == "customer_id"
    assert field_lookup["customer_id"].recommended_data_type == "string"

    assert field_lookup["snapshot_dt"].mapping_source == "naming_enhancement"
    assert field_lookup["snapshot_dt"].recommended_stg_field_name == "snapshot_date"
    assert field_lookup["snapshot_dt"].recommended_data_type == "date"

    assert field_lookup["batch_no"].mapping_source == "original_fallback"
    assert field_lookup["batch_no"].recommended_stg_field_name == "batch_no"
    assert field_lookup["batch_no"].action == "keep"
    assert field_lookup["batch_no"].recommended_data_type == "bigint"

    issue_types = {issue.issue_type for issue in result.issues}
    assert "stg_field_technical_reservation" in issue_types
    assert "stg_table_requires_manual_review" in issue_types


def test_stg_structure_override_edit_replaces_field_name_and_type() -> None:
    skill = StgStructureSuggestionSkill()
    tables = [
        TableMeta(
            table_name="ods_customer_snapshot",
            fields=[
                FieldMeta(
                    field_name="snapshot_dt",
                    field_name_cn="snapshot date",
                    data_type="date",
                    nullable=False,
                )
            ],
        )
    ]

    result = skill.run(
        StgStructureSuggestionInput(
            tables=tables,
            mapping_results=[],
            naming_field_suggestions={
                "ods_customer_snapshot.snapshot_dt": "snapshot_date",
            },
            apply_overrides=True,
            override_records=[
                StgReviewRecord(
                    source_table_name="ods_customer_snapshot",
                    source_field_name="snapshot_dt",
                    original_recommended_stg_field_name="snapshot_date",
                    final_stg_field_name="snapshot_business_date",
                    original_recommended_data_type="date",
                    final_data_type="timestamp",
                    review_action="edit",
                    reviewer_note="keep business date wording but use timestamp",
                    reviewed_at="2026-05-01T10:00:00",
                    source="test",
                )
            ],
        )
    )

    assert result.confirmed_stg_suggestions
    assert result.review_applied_count == 1
    assert result.confirmed_stg_suggestions[0].recommended_stg_field_name == "snapshot_business_date"
    assert result.confirmed_stg_suggestions[0].recommended_data_type == "timestamp"
    assert result.confirmed_stg_suggestions[0].confirmed_source == "override_edit"
