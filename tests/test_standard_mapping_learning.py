"""Tests for learned standard-mapping memory."""

from pathlib import Path

import pytest

from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    clear_standard_mapping_memory_by_field_key,
    explain_standard_mapping_memory_lookup,
    learn_standard_mapping_memory_from_review_records,
    load_standard_mapping_memory,
    lookup_learned_standard_mapping,
    prune_invalid_standard_mapping_memory,
    standard_mapping_memory_details,
    summarize_standard_mapping_memory,
)
from app.core.utils import file_utils
from app.core.utils.file_utils import LocalPathAccessError


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
    assert memory.iloc[0]["table_key"] == "order_header"
    assert memory.iloc[0]["standard_code"] == "customer_name"
    assert lookup_learned_standard_mapping(
        "buyer_name",
        memory,
        table_name="order_header",
    ).standard_code == "customer_name"
    assert lookup_learned_standard_mapping(
        "buyer_status",
        memory,
        table_name="order_header",
    ) is None


def test_standard_mapping_learning_rejects_output_dir_outside_allowed_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(LocalPathAccessError):
        learn_standard_mapping_memory_from_review_records([], output_dir=outside_dir)

    assert not outside_dir.exists()


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
    assert lookup_learned_standard_mapping(
        "buyer_name",
        memory,
        table_name="order_header",
    ).standard_code == "customer_name"


def test_learning_memory_does_not_cross_reuse_generic_field_names(
    tmp_path: Path,
) -> None:
    summary = learn_standard_mapping_memory_from_review_records(
        [
            MappingReviewRecord(
                table_name="contract_info",
                field_name="status",
                original_recommended_standard_code="status_code",
                final_standard_code="contract_status",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            )
        ],
        output_dir=tmp_path,
    )
    memory = load_standard_mapping_memory(Path(summary.output_path))

    same_table_match = lookup_learned_standard_mapping(
        "status",
        memory,
        table_name="contract_info",
    )
    cross_table_match = lookup_learned_standard_mapping(
        "status",
        memory,
        table_name="customer_profile",
    )

    assert same_table_match is not None
    assert same_table_match.match_scope == "table_field"
    assert cross_table_match is None
    blocked_lookup = explain_standard_mapping_memory_lookup(
        "status",
        memory,
        table_name="customer_profile",
    )
    assert blocked_lookup.status == "generic_cross_table_blocked"
    assert "blocked_generic_cross_table" in " ".join(blocked_lookup.evidence)


def test_learning_memory_can_cross_reuse_specific_field_names(
    tmp_path: Path,
) -> None:
    summary = learn_standard_mapping_memory_from_review_records(
        [
            MappingReviewRecord(
                table_name="order_header",
                field_name="buyer_name",
                original_recommended_standard_code="customer_name",
                final_standard_code="customer_name",
                review_action="accept",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            )
        ],
        output_dir=tmp_path,
    )
    memory = load_standard_mapping_memory(Path(summary.output_path))

    learned = lookup_learned_standard_mapping(
        "buyer_name",
        memory,
        table_name="invoice_header",
    )

    assert learned is not None
    assert learned.standard_code == "customer_name"
    assert learned.match_scope == "field"
    lookup = explain_standard_mapping_memory_lookup(
        "buyer_name",
        memory,
        table_name="invoice_header",
    )
    assert lookup.status == "matched"
    assert lookup.learned_mapping is not None
    assert "learned_mapping_memory=matched" in lookup.evidence


def test_learning_memory_blocks_cross_reuse_when_field_history_conflicts(
    tmp_path: Path,
) -> None:
    summary = learn_standard_mapping_memory_from_review_records(
        [
            MappingReviewRecord(
                table_name="order_header",
                field_name="buyer_name",
                original_recommended_standard_code="customer_name",
                final_standard_code="customer_name",
                review_action="accept",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:00:00",
                source="test",
            ),
            MappingReviewRecord(
                table_name="merchant_order",
                field_name="buyer_name",
                original_recommended_standard_code="customer_name",
                final_standard_code="merchant_name",
                review_action="edit",
                reviewer_note=None,
                reviewed_at="2026-06-01T10:01:00",
                source="test",
            ),
        ],
        output_dir=tmp_path,
    )
    memory = load_standard_mapping_memory(Path(summary.output_path))

    same_table = lookup_learned_standard_mapping(
        "buyer_name",
        memory,
        table_name="order_header",
    )
    cross_table = lookup_learned_standard_mapping(
        "buyer_name",
        memory,
        table_name="invoice_header",
    )

    assert same_table is not None
    assert same_table.standard_code == "customer_name"
    assert same_table.match_scope == "table_field"
    assert same_table.conflict_count == 1
    assert cross_table is None
    blocked_lookup = explain_standard_mapping_memory_lookup(
        "buyer_name",
        memory,
        table_name="invoice_header",
    )
    assert blocked_lookup.status == "conflict_cross_table_blocked"
    assert blocked_lookup.conflict_count == 1
    assert "blocked_conflict_cross_table" in " ".join(blocked_lookup.evidence)


def test_standard_mapping_memory_health_flags_conflicts_and_invalid_rows() -> None:
    import pandas as pd

    memory = pd.DataFrame(
        [
            {
                "table_key": "order_header",
                "field_key": "buyer_name",
                "table_name": "order_header",
                "field_name": "buyer_name",
                "standard_code": "customer_name",
            },
            {
                "table_key": "merchant_order",
                "field_key": "buyer_name",
                "table_name": "merchant_order",
                "field_name": "buyer_name",
                "standard_code": "merchant_name",
            },
            {
                "table_key": "contract_info",
                "field_key": "status",
                "table_name": "contract_info",
                "field_name": "status",
                "standard_code": "status_code",
            },
            {
                "table_key": "",
                "field_key": "broken_field",
                "table_name": "broken",
                "field_name": "broken_field",
                "standard_code": "",
            },
        ]
    )

    health = summarize_standard_mapping_memory(memory)

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


def test_standard_mapping_memory_details_and_prune_invalid(tmp_path: Path) -> None:
    import pandas as pd

    memory = pd.DataFrame(
        [
            {
                "table_key": "order_header",
                "field_key": "buyer_name",
                "table_name": "order_header",
                "field_name": "buyer_name",
                "standard_code": "customer_name",
            },
            {
                "table_key": "merchant_order",
                "field_key": "buyer_name",
                "table_name": "merchant_order",
                "field_name": "buyer_name",
                "standard_code": "merchant_name",
            },
            {
                "table_key": "contract_info",
                "field_key": "status",
                "table_name": "contract_info",
                "field_name": "status",
                "standard_code": "status_code",
            },
            {
                "table_key": "",
                "field_key": "broken_field",
                "table_name": "broken",
                "field_name": "broken_field",
                "standard_code": "",
            },
        ]
    )
    details = standard_mapping_memory_details(memory)
    memory_path = tmp_path / "standard_mapping_memory.csv"
    memory.to_csv(memory_path, index=False, encoding="utf-8")

    prune_result = prune_invalid_standard_mapping_memory(memory_path)
    cleaned = load_standard_mapping_memory(memory_path)

    assert len(details["conflict_records"]) == 2
    assert len(details["generic_records"]) == 1
    assert len(details["invalid_records"]) == 1
    assert prune_result["removed_count"] == 1
    assert len(cleaned) == 3


def test_clear_standard_mapping_memory_by_field_key(tmp_path: Path) -> None:
    import pandas as pd

    memory_path = tmp_path / "standard_mapping_memory.csv"
    pd.DataFrame(
        [
            {
                "table_key": "order_header",
                "field_key": "buyer_name",
                "table_name": "order_header",
                "field_name": "buyer_name",
                "standard_code": "customer_name",
            },
            {
                "table_key": "merchant_order",
                "field_key": "buyer_name",
                "table_name": "merchant_order",
                "field_name": "buyer_name",
                "standard_code": "merchant_name",
            },
            {
                "table_key": "contract_info",
                "field_key": "status",
                "table_name": "contract_info",
                "field_name": "status",
                "standard_code": "status_code",
            },
        ]
    ).to_csv(memory_path, index=False, encoding="utf-8")

    result = clear_standard_mapping_memory_by_field_key("buyer_name", memory_path)
    cleaned = load_standard_mapping_memory(memory_path)

    assert result["status"] == "cleared"
    assert result["removed_count"] == 2
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["field_key"] == "status"
