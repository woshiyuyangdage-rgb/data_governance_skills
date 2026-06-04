"""Facade for learned-memory health summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    StandardMappingMemoryHealth,
    clear_standard_mapping_memory_by_field_key,
    prune_invalid_standard_mapping_memory,
    summarize_standard_mapping_memory,
    standard_mapping_memory_details,
)
from app.core.skills.stg_standardization_skill.stg_learning import (
    StgMemoryHealth,
    clear_stg_field_memory_by_field_key,
    prune_invalid_stg_field_memory,
    summarize_stg_field_memory,
    stg_field_memory_details,
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

    def details(self) -> dict[str, object]:
        """Return learned-memory records that need maintenance attention."""
        return {
            "standard_mapping": standard_mapping_memory_details(),
            "stg_standardization": stg_field_memory_details(),
        }

    def prune_invalid(self) -> dict[str, object]:
        """Remove clearly invalid learned-memory records from local CSV stores."""
        standard_mapping = prune_invalid_standard_mapping_memory()
        stg_standardization = prune_invalid_stg_field_memory()
        total_removed = int(standard_mapping["removed_count"]) + int(
            stg_standardization["removed_count"]
        )
        return {
            "standard_mapping": standard_mapping,
            "stg_standardization": stg_standardization,
            "total_removed_count": total_removed,
            "summary": f"Removed {total_removed} invalid learning-memory records.",
        }

    def clear_field_key(self, memory_type: str, field_key: str) -> dict[str, object]:
        """Clear learned memory for one field key in one memory domain."""
        normalized_type = str(memory_type or "").strip().lower()
        if normalized_type in {"standard_mapping", "mapping"}:
            result = clear_standard_mapping_memory_by_field_key(field_key)
            result["memory_type"] = "standard_mapping"
            return result
        if normalized_type in {"stg_standardization", "stg"}:
            result = clear_stg_field_memory_by_field_key(field_key)
            result["memory_type"] = "stg_standardization"
            return result
        raise ValueError(
            "memory_type must be one of: standard_mapping, stg_standardization"
        )
