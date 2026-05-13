"""Tests for local quality rule override persistence."""

from pathlib import Path

from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.review import quality_override_store


def _patch_quality_override_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_OVERRIDES_PATH",
        tmp_path / "quality_rule_overrides.csv",
    )
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_SESSIONS_DIR",
        tmp_path / "quality_rule_sessions",
    )


def test_quality_override_store_returns_empty_when_file_does_not_exist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_quality_override_paths(tmp_path, monkeypatch)

    assert quality_override_store.load_quality_rule_overrides() == []


def test_quality_override_store_can_save_load_and_lookup_records(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_quality_override_paths(tmp_path, monkeypatch)
    records = [
        QualityRuleReviewRecord(
            source_table_name="sales_order",
            source_field_name="order_id",
            rule_type="not_null",
            original_rule_expression="not_null",
            final_rule_expression="not_null",
            original_severity="high",
            final_severity="high",
            review_action="accept",
            reviewer_note="confirmed",
            reviewed_at="2026-05-01T10:00:00",
            source="test",
        )
    ]

    result = quality_override_store.save_quality_rule_review_records(records)
    loaded = quality_override_store.load_quality_rule_overrides()
    lookup = quality_override_store.build_quality_rule_override_lookup(loaded)

    assert result["saved_count"] == 1
    assert len(loaded) == 1
    assert lookup["sales_order.order_id.not_null"].review_action == "accept"
    assert Path(str(result["history_path"])).exists()
