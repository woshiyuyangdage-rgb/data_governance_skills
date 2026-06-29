"""Tests for learned STG field memory."""

from pathlib import Path

from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.skills.stg_standardization_skill.stg_learning import (
    apply_learned_stg_field,
    clear_stg_field_memory_by_field_key,
    explain_stg_memory_lookup,
    learn_stg_memory_from_review_records,
    load_stg_field_memory,
    lookup_learned_stg_field,
    prune_invalid_stg_field_memory,
    stg_field_memory_details,
    summarize_stg_field_memory,
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
    assert memory.iloc[0]["table_key"] == "ods_customer_snapshot"
    learned = lookup_learned_stg_field(
        "snapshot_dt",
        memory,
        source_table_name="ods_customer_snapshot",
    )
    assert learned is not None
    assert learned.final_stg_field_name == "snapshot_business_date"
    assert learned.final_data_type == "timestamp"
    assert lookup_learned_stg_field(
        "batch_no",
        memory,
        source_table_name="ods_customer_snapshot",
    ) is None


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
        source_table_name="ods_customer_snapshot",
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


def test_stg_learning_does_not_cross_reuse_generic_field_names(
    tmp_path: Path,
) -> None:
    summary = learn_stg_memory_from_review_records(
        [
            StgReviewRecord(
                source_table_name="contract_info",
                source_field_name="status",
                original_recommended_stg_field_name="contract_status",
                final_stg_field_name="contract_status_code",
                original_recommended_data_type="varchar",
                final_data_type="varchar",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            )
        ],
        output_dir=tmp_path,
    )
    memory = load_stg_field_memory(Path(summary.output_path))

    same_table_match = lookup_learned_stg_field(
        "status",
        memory,
        source_table_name="contract_info",
    )
    cross_table_match = lookup_learned_stg_field(
        "status",
        memory,
        source_table_name="customer_profile",
    )

    assert same_table_match is not None
    assert same_table_match.match_scope == "table_field"
    assert cross_table_match is None
    blocked_lookup = explain_stg_memory_lookup(
        "status",
        memory,
        source_table_name="customer_profile",
    )
    assert blocked_lookup.status == "generic_cross_table_blocked"
    assert "blocked_generic_cross_table" in " ".join(blocked_lookup.evidence)


def test_stg_learning_can_cross_reuse_specific_field_names(tmp_path: Path) -> None:
    summary = learn_stg_memory_from_review_records(
        [
            StgReviewRecord(
                source_table_name="ods_order_header",
                source_field_name="snapshot_dt",
                original_recommended_stg_field_name="snapshot_date",
                final_stg_field_name="snapshot_business_date",
                original_recommended_data_type="date",
                final_data_type="date",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            )
        ],
        output_dir=tmp_path,
    )
    memory = load_stg_field_memory(Path(summary.output_path))

    learned = lookup_learned_stg_field(
        "snapshot_dt",
        memory,
        source_table_name="ods_invoice_header",
    )

    assert learned is not None
    assert learned.final_stg_field_name == "snapshot_business_date"
    assert learned.match_scope == "field"
    lookup = explain_stg_memory_lookup(
        "snapshot_dt",
        memory,
        source_table_name="ods_invoice_header",
    )
    assert lookup.status == "matched"
    assert lookup.learned_field is not None
    assert "learned_stg_memory=matched" in lookup.evidence


def test_stg_learning_blocks_cross_reuse_when_field_history_conflicts(
    tmp_path: Path,
) -> None:
    summary = learn_stg_memory_from_review_records(
        [
            StgReviewRecord(
                source_table_name="ods_order_header",
                source_field_name="buyer_name",
                original_recommended_stg_field_name="buyer_name",
                final_stg_field_name="customer_name",
                original_recommended_data_type="varchar",
                final_data_type="varchar",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            ),
            StgReviewRecord(
                source_table_name="ods_merchant_order",
                source_field_name="buyer_name",
                original_recommended_stg_field_name="buyer_name",
                final_stg_field_name="merchant_name",
                original_recommended_data_type="varchar",
                final_data_type="varchar",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:01:00",
                source="test",
            ),
        ],
        output_dir=tmp_path,
    )
    memory = load_stg_field_memory(Path(summary.output_path))

    same_table = lookup_learned_stg_field(
        "buyer_name",
        memory,
        source_table_name="ods_order_header",
    )
    cross_table = lookup_learned_stg_field(
        "buyer_name",
        memory,
        source_table_name="ods_invoice_header",
    )

    assert same_table is not None
    assert same_table.final_stg_field_name == "customer_name"
    assert same_table.match_scope == "table_field"
    assert same_table.conflict_count == 1
    assert cross_table is None
    blocked_lookup = explain_stg_memory_lookup(
        "buyer_name",
        memory,
        source_table_name="ods_invoice_header",
    )
    assert blocked_lookup.status == "conflict_cross_table_blocked"
    assert blocked_lookup.conflict_count == 1
    assert "blocked_conflict_cross_table" in " ".join(blocked_lookup.evidence)


def test_stg_memory_health_flags_conflicts_and_invalid_rows() -> None:
    import pandas as pd

    memory = pd.DataFrame(
        [
            {
                "table_key": "ods_order_header",
                "field_key": "buyer_name",
                "source_table_name": "ods_order_header",
                "source_field_name": "buyer_name",
                "final_stg_field_name": "customer_name",
            },
            {
                "table_key": "ods_merchant_order",
                "field_key": "buyer_name",
                "source_table_name": "ods_merchant_order",
                "source_field_name": "buyer_name",
                "final_stg_field_name": "merchant_name",
            },
            {
                "table_key": "contract_info",
                "field_key": "status",
                "source_table_name": "contract_info",
                "source_field_name": "status",
                "final_stg_field_name": "contract_status_code",
            },
            {
                "table_key": "",
                "field_key": "broken_field",
                "source_table_name": "broken",
                "source_field_name": "broken_field",
                "final_stg_field_name": "",
            },
        ]
    )

    health = summarize_stg_field_memory(memory)

    assert health.memory_count == 4
    assert health.field_key_count == 3
    assert health.table_key_count == 3
    assert health.reusable_field_count == 1
    assert health.generic_field_count == 1
    assert health.conflict_field_count == 1
    assert health.invalid_record_count == 1
    assert health.conflict_field_keys == ("buyer_name",)
    assert "status" in health.generic_field_keys
    assert "missing_table:broken_field" in health.invalid_record_keys


def test_stg_memory_details_and_prune_invalid(tmp_path: Path) -> None:
    import pandas as pd

    memory = pd.DataFrame(
        [
            {
                "table_key": "ods_order_header",
                "field_key": "buyer_name",
                "source_table_name": "ods_order_header",
                "source_field_name": "buyer_name",
                "final_stg_field_name": "customer_name",
            },
            {
                "table_key": "ods_merchant_order",
                "field_key": "buyer_name",
                "source_table_name": "ods_merchant_order",
                "source_field_name": "buyer_name",
                "final_stg_field_name": "merchant_name",
            },
            {
                "table_key": "contract_info",
                "field_key": "status",
                "source_table_name": "contract_info",
                "source_field_name": "status",
                "final_stg_field_name": "contract_status_code",
            },
            {
                "table_key": "",
                "field_key": "broken_field",
                "source_table_name": "broken",
                "source_field_name": "broken_field",
                "final_stg_field_name": "",
            },
        ]
    )
    details = stg_field_memory_details(memory)
    memory_path = tmp_path / "stg_field_memory.csv"
    memory.to_csv(memory_path, index=False, encoding="utf-8")

    prune_result = prune_invalid_stg_field_memory(memory_path)
    cleaned = load_stg_field_memory(memory_path)

    assert len(details["conflict_records"]) == 2
    assert len(details["generic_records"]) == 1
    assert len(details["invalid_records"]) == 1
    assert prune_result["removed_count"] == 1
    assert len(cleaned) == 3


def test_clear_stg_field_memory_by_field_key(tmp_path: Path) -> None:
    import pandas as pd

    memory_path = tmp_path / "stg_field_memory.csv"
    pd.DataFrame(
        [
            {
                "table_key": "ods_order_header",
                "field_key": "buyer_name",
                "source_table_name": "ods_order_header",
                "source_field_name": "buyer_name",
                "final_stg_field_name": "customer_name",
            },
            {
                "table_key": "ods_merchant_order",
                "field_key": "buyer_name",
                "source_table_name": "ods_merchant_order",
                "source_field_name": "buyer_name",
                "final_stg_field_name": "merchant_name",
            },
            {
                "table_key": "contract_info",
                "field_key": "status",
                "source_table_name": "contract_info",
                "source_field_name": "status",
                "final_stg_field_name": "contract_status_code",
            },
        ]
    ).to_csv(memory_path, index=False, encoding="utf-8")

    result = clear_stg_field_memory_by_field_key("buyer_name", memory_path)
    cleaned = load_stg_field_memory(memory_path)

    assert result["status"] == "cleared"
    assert result["removed_count"] == 2
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["field_key"] == "status"
