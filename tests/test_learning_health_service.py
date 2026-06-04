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
