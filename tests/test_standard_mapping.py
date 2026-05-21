"""Tests for the P1 standard mapping recommendation skill."""

from pathlib import Path

from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.orchestrator.pipeline_service import run_p0_plus_mapping_from_file
from app.core.skills.data_standard_mapping_skill import (
    StandardMappingInput,
    StandardMappingRecommendationSkill,
)
from app.core.skills.data_standard_mapping_skill import semantic_index
from app.core.skills.data_standard_mapping_skill import standard_mapping_recommendation

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_standard_mapping_skill_maps_known_fields() -> None:
    skill = StandardMappingRecommendationSkill()
    tables = [
        TableMeta(
            table_name="customer_master",
            fields=[
                FieldMeta(field_name="customer_id", field_name_cn="customer id"),
                FieldMeta(field_name="customer_name", field_name_cn="customer name"),
                FieldMeta(field_name="event_trace_code", field_name_cn="event trace code"),
            ],
        )
    ]

    result = skill.run(StandardMappingInput(tables=tables))

    mapped_codes = {item.recommended_standard_code for item in result.mapping_results}
    assert "customer_id" in mapped_codes
    assert "customer_name" in mapped_codes
    assert result.summary
    assert any(
        unmapped.field_name == "event_trace_code" for unmapped in result.unmapped_fields
    )


def test_run_p0_plus_mapping_from_sample_file_returns_mapping_payload() -> None:
    result = run_p0_plus_mapping_from_file(str(SAMPLE_METADATA_PATH))

    assert result.mapping_results
    assert any(item.recommended_standard_code == "customer_id" for item in result.mapping_results)
    assert result.mapping_summary


def test_standard_mapping_override_is_applied_before_confirmed_output() -> None:
    skill = StandardMappingRecommendationSkill()
    tables = [
        TableMeta(
            table_name="sales_order",
            fields=[FieldMeta(field_name="Order__ID", field_name_cn="order id")],
        )
    ]

    result = skill.run(
        StandardMappingInput(
            tables=tables,
            apply_overrides=True,
            override_records=[
                MappingReviewRecord(
                    table_name="sales_order",
                    field_name="Order__ID",
                    original_recommended_standard_code="transaction_id",
                    final_standard_code="audit_log_id",
                    review_action="edit",
                    reviewer_note="business requested audit id reuse",
                    reviewed_at="2026-05-01T10:00:00",
                    source="test",
                )
            ],
        )
    )

    assert result.confirmed_mapping_results
    assert result.review_applied_count == 1
    assert result.confirmed_mapping_results[0].recommended_standard_code == "audit_log_id"
    assert result.confirmed_mapping_results[0].confirmed_source == "override_edit"


def test_semantic_match_can_promote_low_rule_score_to_mapping(monkeypatch) -> None:
    skill = StandardMappingRecommendationSkill()
    tables = [
        TableMeta(
            table_name="customer_master",
            fields=[FieldMeta(field_name="buyer_name", field_name_cn="buyer name")],
        )
    ]

    semantic_match = semantic_index.SemanticFieldMatch(
        field_text="buyer_name | buyer name",
        best_match=semantic_index.SemanticMatch(
            standard_code="customer_name",
            standard_name="customer_name",
            standard_name_cn="customer name",
            score=0.86,
            rank=1,
        ),
        top_matches=[
            semantic_index.SemanticMatch(
                standard_code="customer_name",
                standard_name="customer_name",
                standard_name_cn="customer name",
                score=0.86,
                rank=1,
            )
        ],
        threshold=0.85,
        enabled=True,
    )

    monkeypatch.setattr(
        standard_mapping_recommendation,
        "semantic_match_source_fields",
        lambda fields, candidate_limit=None: [semantic_match for _ in fields],
    )

    result = skill.run(StandardMappingInput(tables=tables, apply_overrides=False))

    assert result.mapping_results
    assert result.mapping_results[0].recommended_standard_code == "customer_name"
    assert result.mapping_results[0].match_score == 0.86
    assert all(
        unmapped.field_name != "buyer_name" for unmapped in result.unmapped_fields
    )
