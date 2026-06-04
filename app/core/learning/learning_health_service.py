"""Facade for learned-memory health summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    StandardMappingMemoryHealth,
    summarize_standard_mapping_memory,
)
from app.core.skills.stg_standardization_skill.stg_learning import (
    StgMemoryHealth,
    summarize_stg_field_memory,
)


@dataclass(frozen=True)
class LearningHealthOverview:
    """Combined maintenance view for all local learning memories."""

    standard_mapping: StandardMappingMemoryHealth
    stg_standardization: StgMemoryHealth
    total_memory_count: int
    total_conflict_field_count: int
    total_invalid_record_count: int
    summary: str

    def model_dump(self) -> dict[str, object]:
        """Return a JSON-friendly payload similar to Pydantic models."""
        return {
            "standard_mapping": asdict(self.standard_mapping),
            "stg_standardization": asdict(self.stg_standardization),
            "total_memory_count": self.total_memory_count,
            "total_conflict_field_count": self.total_conflict_field_count,
            "total_invalid_record_count": self.total_invalid_record_count,
            "summary": self.summary,
        }


class LearningHealthService:
    """Build health summaries for local learning memories."""

    def summarize(self) -> LearningHealthOverview:
        """Summarize standard mapping and STG learning memory health."""
        standard_mapping = summarize_standard_mapping_memory()
        stg_standardization = summarize_stg_field_memory()
        total_memory_count = (
            standard_mapping.memory_count + stg_standardization.memory_count
        )
        total_conflict_field_count = (
            standard_mapping.conflict_field_count
            + stg_standardization.conflict_field_count
        )
        total_invalid_record_count = (
            standard_mapping.invalid_record_count
            + stg_standardization.invalid_record_count
        )
        summary = (
            f"Learning memory contains {total_memory_count} records across "
            "standard mapping and STG standardization. "
            f"{total_conflict_field_count} field keys have conflicting targets and "
            f"{total_invalid_record_count} invalid records need maintenance."
        )
        return LearningHealthOverview(
            standard_mapping=standard_mapping,
            stg_standardization=stg_standardization,
            total_memory_count=total_memory_count,
            total_conflict_field_count=total_conflict_field_count,
            total_invalid_record_count=total_invalid_record_count,
            summary=summary,
        )
