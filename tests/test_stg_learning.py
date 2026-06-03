"""Tests for learned STG field memory."""

from pathlib import Path

from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.skills.stg_standardization_skill.stg_learning import (
    apply_learned_stg_field,
    learn_stg_memory_from_review_records,
    load_stg_field_memory,
    lookup_learned_stg_field,
)


def test_stg_learning_memory_saves_only_confirmed_reviews(tmp_path: Path) -> None:
    records = [
        StgReviewRecord(
            source_table_name="ods_customer_snapshot",
            source_field_name="snapshot_dt",
            original_recommended_stg_field_name="snapshot_date",
            final_stg_field_name="snapshot_business_date",
            original_recommended_data_type="date",
            final_data_type="timestamp",
            review_action="edit",
            reviewer_note="business naming preferred",
            reviewed_at="2026-06-01T10:00:00",
            source="test",
        ),
        StgReviewRecord(
            source_table_name="ods_customer_snapshot",
            source_field_name="batch_no",
            original_recommended_stg_field_name="batch_no",
            final_stg_field_name=None,
            original_recommended_data_type="bigint",
            final_data_type=None,
            review_action="mark_for_manual_review",
            reviewer_note="needs steward",
            reviewed_at="2026-06-01T10:01:00",
            source="test",
        ),
    ]

    summary = learn_stg_memory_from_review_records(records, output_dir=tmp_path)
    memory = load_stg_field_memory(Path(summary.output_path))

    assert summary.learned_count == 1
    assert len(memory) == 1
    learned = lookup_learned_stg_field("snapshot_dt", memory)
    assert learned is not None
    assert learned.final_stg_field_name == "snapshot_business_date"
    assert learned.final_data_type == "timestamp"
    assert lookup_learned_stg_field("batch_no", memory) is None


def test_apply_learned_stg_field_updates_suggestion_without_confirming(
    tmp_path: Path,
) -> None:
    memory_summary = learn_stg_memory_from_review_records(
        [
            StgReviewRecord(
                source_table_name="ods_customer_snapshot",
                source_field_name="snapshot_dt",
                original_recommended_stg_field_name="snapshot_date",
                final_stg_field_name="snapshot_business_date",
                original_recommended_data_type="date",
                final_data_type="timestamp",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            )
        ],
        output_dir=tmp_path,
    )
    learned = lookup_learned_stg_field(
        "snapshot_dt",
        load_stg_field_memory(memory_summary.output_path),
    )

    suggestion = StgFieldSuggestion(
        source_table_name="ods_customer_snapshot",
        source_field_name="snapshot_dt",
        source_data_type="date",
        recommended_stg_field_name="snapshot_date",
        recommended_data_type="date",
        mapping_source="naming_enhancement",
        action="rename",
    )
    updated = apply_learned_stg_field(suggestion, learned)

    assert updated.recommended_stg_field_name == "snapshot_business_date"
    assert updated.recommended_data_type == "timestamp"
    assert updated.mapping_source == "learned_stg_memory"
    assert updated.confirmed_source is None
    assert "learned_from_stg_review_history" in (updated.notes or "")
