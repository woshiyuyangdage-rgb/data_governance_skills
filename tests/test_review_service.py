"""Tests for review record helpers and override application."""

from app.core.models.mapping_result import MappingResult
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.review.review_service import (
    apply_mapping_overrides_to_results,
    apply_stg_overrides_to_suggestions,
    build_mapping_review_records_from_results,
    build_stg_review_records_from_results,
    summarize_review_records,
)


def test_review_service_builds_records_and_summary() -> None:
    mapping_results = [
        MappingResult(
            table_name="sales_order",
            field_name="order_id",
            recommended_standard_code="transaction_id",
            recommended_standard_name="transaction_id",
            match_score=0.95,
            match_reason="exact",
            candidate_count=1,
        )
    ]
    stg_suggestions = [
        StgFieldSuggestion(
            source_table_name="sales_order",
            source_field_name="order_id",
            source_data_type="string",
            recommended_stg_field_name="transaction_id",
            recommended_data_type="string",
            nullable=False,
            mapping_source="standard_mapping",
            action="rename",
        )
    ]

    mapping_records = build_mapping_review_records_from_results(
        mapping_results,
        {
            "sales_order.order_id": {
                "review_action": "edit",
                "final_standard_code": "transaction_id",
                "reviewer_note": "confirmed",
            }
        },
        source="test",
    )
    stg_records = build_stg_review_records_from_results(
        stg_suggestions,
        {
            "sales_order.order_id": {
                "review_action": "mark_for_manual_review",
                "final_stg_field_name": "transaction_id",
                "final_data_type": "string",
                "reviewer_note": "check with modeler",
            }
        },
        source="test",
    )
    summary = summarize_review_records(mapping_records, stg_records)

    assert mapping_records[0].review_action == "edit"
    assert mapping_records[0].config_fingerprint
    assert mapping_records[0].standard_set_version
    assert mapping_records[0].source_field_hash
    assert stg_records[0].review_action == "mark_for_manual_review"
    assert stg_records[0].config_fingerprint
    assert stg_records[0].source_field_hash
    assert summary.edited_count == 1
    assert summary.manual_review_count == 1
    assert summary.total_reviewed_count == 2


def test_review_service_applies_overrides() -> None:
    mapping_results = [
        MappingResult(
            table_name="sales_order",
            field_name="order_id",
            recommended_standard_code="transaction_id",
            recommended_standard_name="transaction_id",
            match_score=0.95,
            match_reason="exact",
            candidate_count=1,
        )
    ]
    stg_suggestions = [
        StgFieldSuggestion(
            source_table_name="sales_order",
            source_field_name="order_id",
            source_data_type="string",
            recommended_stg_field_name="transaction_id",
            recommended_data_type="string",
            nullable=False,
            mapping_source="standard_mapping",
            action="rename",
            notes="Derived from standard mapping.",
        )
    ]

    confirmed_mapping, mapping_count, _ = apply_mapping_overrides_to_results(
        mapping_results,
        [
            MappingReviewRecord(
                table_name="sales_order",
                field_name="order_id",
                original_recommended_standard_code="transaction_id",
                final_standard_code="transaction_id",
                review_action="mark_for_manual_review",
                reviewer_note="check",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ],
    )
    confirmed_stg, stg_count, _ = apply_stg_overrides_to_suggestions(
        stg_suggestions,
        [
            StgReviewRecord(
                source_table_name="sales_order",
                source_field_name="order_id",
                original_recommended_stg_field_name="transaction_id",
                final_stg_field_name="stg_transaction_id",
                original_recommended_data_type="string",
                final_data_type="string",
                review_action="edit",
                reviewer_note="prefix requested",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ],
    )

    assert mapping_count == 1
    assert confirmed_mapping[0].confirmed_source == "override_manual_review"
    assert stg_count == 1
    assert confirmed_stg[0].recommended_stg_field_name == "stg_transaction_id"
    assert confirmed_stg[0].confirmed_source == "override_edit"


def test_review_service_marks_stale_mapping_override_for_review() -> None:
    original_result = MappingResult(
        table_name="sales_order",
        field_name="order_id",
        recommended_standard_code="transaction_id",
        recommended_standard_name="transaction_id",
        match_score=0.95,
        match_reason="exact",
        context_evidence=["field_data_type=varchar"],
        candidate_count=1,
    )
    record = build_mapping_review_records_from_results(
        [original_result],
        {"sales_order.order_id": {"review_action": "accept"}},
        source="test",
    )[0]
    changed_result = original_result.model_copy(
        update={"context_evidence": ["field_data_type=decimal"]}
    )

    confirmed_mapping, mapping_count, _ = apply_mapping_overrides_to_results(
        [changed_result],
        [record],
    )

    assert mapping_count == 0
    assert confirmed_mapping[0].confirmed_source == "override_stale_review_required"
    assert confirmed_mapping[0].mapping_status == "stale_review_required"
    assert confirmed_mapping[0].requires_manual_review is True
    assert "source_field_hash" in (confirmed_mapping[0].reviewer_note or "")


def test_review_service_marks_stale_stg_override_for_review() -> None:
    original_suggestion = StgFieldSuggestion(
        source_table_name="sales_order",
        source_field_name="order_id",
        source_data_type="string",
        recommended_stg_field_name="transaction_id",
        recommended_data_type="string",
        nullable=False,
        mapping_source="standard_mapping",
        action="rename",
    )
    record = build_stg_review_records_from_results(
        [original_suggestion],
        {"sales_order.order_id": {"review_action": "accept"}},
        source="test",
    )[0]
    changed_suggestion = original_suggestion.model_copy(
        update={"recommended_data_type": "decimal"}
    )

    confirmed_stg, stg_count, _ = apply_stg_overrides_to_suggestions(
        [changed_suggestion],
        [record],
    )

    assert stg_count == 0
    assert confirmed_stg[0].confirmed_source == "override_stale_review_required"
    assert confirmed_stg[0].review_action == "stale_review_required"
    assert confirmed_stg[0].action == "manual_review_required"
    assert "source_field_hash" in (confirmed_stg[0].reviewer_note or "")
