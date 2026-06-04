"""Tests for learned-memory health service."""

from app.core.learning import learning_health_service
from app.core.learning.learning_health_service import LearningHealthService
from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    StandardMappingMemoryHealth,
)
from app.core.skills.stg_standardization_skill.stg_learning import StgMemoryHealth


def test_learning_health_service_summarizes_all_learning_memories(monkeypatch) -> None:
    monkeypatch.setattr(
        learning_health_service,
        "summarize_standard_mapping_memory",
        lambda: StandardMappingMemoryHealth(
            memory_count=3,
            field_key_count=2,
            table_key_count=2,
            reusable_field_count=1,
            generic_field_count=1,
            conflict_field_count=1,
            invalid_record_count=1,
            conflict_field_keys=("buyer_name",),
            generic_field_keys=("status",),
            invalid_record_keys=("missing_table:broken_mapping",),
        ),
    )
    monkeypatch.setattr(
        learning_health_service,
        "summarize_stg_field_memory",
        lambda: StgMemoryHealth(
            memory_count=4,
            field_key_count=3,
            table_key_count=2,
            reusable_field_count=2,
            generic_field_count=1,
            conflict_field_count=1,
            invalid_record_count=0,
            conflict_field_keys=("buyer_name",),
            generic_field_keys=("status",),
            invalid_record_keys=(),
        ),
    )

    overview = LearningHealthService().summarize()
    payload = overview.model_dump()

    assert overview.total_memory_count == 7
    assert overview.total_conflict_field_count == 2
    assert overview.total_invalid_record_count == 1
    assert "7 records" in overview.summary
    assert payload["standard_mapping"]["memory_count"] == 3
    assert payload["stg_standardization"]["memory_count"] == 4


def test_learning_health_service_returns_details_and_prunes_invalid(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        learning_health_service,
        "standard_mapping_memory_details",
        lambda: {
            "conflict_records": [{"field_key": "buyer_name"}],
            "generic_records": [{"field_key": "status"}],
            "invalid_records": [{"field_key": "broken_mapping"}],
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "stg_field_memory_details",
        lambda: {
            "conflict_records": [],
            "generic_records": [{"field_key": "type"}],
            "invalid_records": [{"field_key": "broken_stg"}],
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "prune_invalid_standard_mapping_memory",
        lambda: {
            "path": "mapping.csv",
            "before_count": 3,
            "removed_count": 1,
            "after_count": 2,
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "prune_invalid_stg_field_memory",
        lambda: {
            "path": "stg.csv",
            "before_count": 4,
            "removed_count": 2,
            "after_count": 2,
        },
    )

    service = LearningHealthService()
    details = service.details()
    prune_result = service.prune_invalid()

    assert details["standard_mapping"]["conflict_records"][0]["field_key"] == "buyer_name"
    assert details["stg_standardization"]["generic_records"][0]["field_key"] == "type"
    assert prune_result["total_removed_count"] == 3
    assert "Removed 3" in prune_result["summary"]


def test_learning_health_service_clears_field_key_by_memory_type(monkeypatch) -> None:
    monkeypatch.setattr(
        learning_health_service,
        "clear_standard_mapping_memory_by_field_key",
        lambda field_key: {
            "field_key": field_key,
            "removed_count": 2,
            "status": "cleared",
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "clear_stg_field_memory_by_field_key",
        lambda field_key: {
            "field_key": field_key,
            "removed_count": 1,
            "status": "cleared",
        },
    )

    service = LearningHealthService()
    mapping_result = service.clear_field_key("standard_mapping", "buyer_name")
    stg_result = service.clear_field_key("stg_standardization", "buyer_name")

    assert mapping_result["memory_type"] == "standard_mapping"
    assert mapping_result["removed_count"] == 2
    assert stg_result["memory_type"] == "stg_standardization"
    assert stg_result["removed_count"] == 1


def test_learning_health_service_rejects_unknown_memory_type() -> None:
    service = LearningHealthService()

    try:
        service.clear_field_key("unknown", "buyer_name")
    except ValueError as exc:
        assert "memory_type must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown memory_type")
