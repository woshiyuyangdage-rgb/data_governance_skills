"""Tests for local override persistence."""

from pathlib import Path

from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.stg_review_record import StgReviewRecord
from app.core.review import override_store


def _patch_override_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "STG_OVERRIDES_PATH",
        tmp_path / "stg_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )


def test_override_store_returns_empty_when_files_do_not_exist(tmp_path: Path, monkeypatch) -> None:
    _patch_override_paths(tmp_path, monkeypatch)

    assert override_store.load_mapping_overrides() == []
    assert override_store.load_stg_overrides() == []


def test_override_store_can_save_load_and_lookup_records(tmp_path: Path, monkeypatch) -> None:
    _patch_override_paths(tmp_path, monkeypatch)

    mapping_records = [
        MappingReviewRecord(
            table_name="sales_order",
            field_name="order_id",
            original_recommended_standard_code="transaction_id",
            final_standard_code="transaction_id",
            review_action="accept",
            reviewer_note="keep as is",
            reviewed_at="2026-05-01T10:00:00",
            source="test",
        )
    ]
    stg_records = [
        StgReviewRecord(
            source_table_name="ods_customer_snapshot",
            source_field_name="snapshot_dt",
            original_recommended_stg_field_name="snapshot_date",
            final_stg_field_name="snapshot_business_date",
            original_recommended_data_type="date",
            final_data_type="date",
            review_action="edit",
            reviewer_note="prefer business date wording",
            reviewed_at="2026-05-01T10:00:00",
            source="test",
        )
    ]

    override_store.save_mapping_review_records(mapping_records)
    override_store.save_stg_review_records(stg_records)

    loaded_mapping = override_store.load_mapping_overrides()
    loaded_stg = override_store.load_stg_overrides()

    assert len(loaded_mapping) == 1
    assert len(loaded_stg) == 1

    mapping_lookup = override_store.build_mapping_override_lookup(loaded_mapping)
    stg_lookup = override_store.build_stg_override_lookup(loaded_stg)

    assert mapping_lookup["sales_order.order_id"].review_action == "accept"
    assert (
        stg_lookup["ods_customer_snapshot.snapshot_dt"].final_stg_field_name
        == "snapshot_business_date"
    )
    assert (tmp_path / "learned_stg" / "stg_field_memory.csv").exists()
