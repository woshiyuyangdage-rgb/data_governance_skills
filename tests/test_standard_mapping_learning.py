"""Tests for learned standard-mapping memory."""

from pathlib import Path

from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    learn_standard_mapping_memory_from_review_records,
    load_standard_mapping_memory,
    lookup_learned_standard_mapping,
)


def test_learning_memory_saves_only_confirmed_mapping_reviews(tmp_path: Path) -> None:
    records = [
        MappingReviewRecord(
            table_name="order_header",
            field_name="buyer_name",
            original_recommended_standard_code="account_id",
            final_standard_code="customer_name",
            review_action="edit",
            reviewer_note="buyer is customer name in this domain",
            reviewed_at="2026-06-01T10:00:00",
            source="test",
        ),
        MappingReviewRecord(
            table_name="order_header",
            field_name="buyer_status",
            original_recommended_standard_code="status_code",
            final_standard_code=None,
            review_action="mark_for_manual_review",
            reviewer_note="needs steward decision",
            reviewed_at="2026-06-01T10:01:00",
            source="test",
        ),
    ]

    summary = learn_standard_mapping_memory_from_review_records(
        records,
        output_dir=tmp_path,
    )
    memory = load_standard_mapping_memory(Path(summary.output_path))

    assert summary.learned_count == 1
    assert len(memory) == 1
    assert memory.iloc[0]["field_key"] == "buyer_name"
    assert memory.iloc[0]["standard_code"] == "customer_name"
    assert lookup_learned_standard_mapping("buyer_name", memory).standard_code == (
        "customer_name"
    )
    assert lookup_learned_standard_mapping("buyer_status", memory) is None


def test_learning_memory_keeps_latest_mapping_for_same_field(tmp_path: Path) -> None:
    learn_standard_mapping_memory_from_review_records(
        [
            MappingReviewRecord(
                table_name="order_header",
                field_name="buyer_name",
                original_recommended_standard_code="account_id",
                final_standard_code="account_id",
                review_action="accept",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            ),
            MappingReviewRecord(
                table_name="order_header",
                field_name="buyer_name",
                original_recommended_standard_code="account_id",
                final_standard_code="customer_name",
                review_action="edit",
                reviewer_note="corrected after review",
                reviewed_at="2026-06-01T10:02:00",
                source="test",
            ),
        ],
        output_dir=tmp_path,
    )

    memory = load_standard_mapping_memory(tmp_path / "standard_mapping_memory.csv")

    assert len(memory) == 1
    assert lookup_learned_standard_mapping("buyer_name", memory).standard_code == (
        "customer_name"
    )
