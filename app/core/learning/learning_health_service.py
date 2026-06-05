"""Facade for learned-memory health summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.core.learning.learning_memory_backup import (
    create_learning_memory_backup,
    list_learning_memory_backups,
)
from app.core.parser.metadata_learning import (
    MetadataCompletionMemoryHealth,
    clear_metadata_completion_memory_by_field_key,
    metadata_completion_memory_details,
    prune_invalid_metadata_completion_memory,
    summarize_metadata_completion_memory,
)
from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
    QualityRuleLearningHealth,
    load_quality_rule_associations,
    summarize_quality_rule_learning,
)
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
    metadata_completion: MetadataCompletionMemoryHealth
    quality_rules: QualityRuleLearningHealth
    total_memory_count: int
    total_conflict_field_count: int
    total_invalid_record_count: int
    summary: str

    def model_dump(self) -> dict[str, object]:
        """Return a JSON-friendly payload similar to Pydantic models."""
        return {
            "standard_mapping": asdict(self.standard_mapping),
            "stg_standardization": asdict(self.stg_standardization),
            "metadata_completion": asdict(self.metadata_completion),
            "quality_rules": asdict(self.quality_rules),
            "total_memory_count": self.total_memory_count,
            "total_conflict_field_count": self.total_conflict_field_count,
            "total_invalid_record_count": self.total_invalid_record_count,
            "summary": self.summary,
        }


class LearningHealthService:
    """Build health summaries for local learning memories."""

    def summarize(self) -> LearningHealthOverview:
        """Summarize local learning memory health across governance skills."""
        standard_mapping = summarize_standard_mapping_memory()
        stg_standardization = summarize_stg_field_memory()
        metadata_completion = summarize_metadata_completion_memory()
        quality_rules = summarize_quality_rule_learning()
        total_memory_count = (
            standard_mapping.memory_count + stg_standardization.memory_count
            + metadata_completion.field_memory_count
            + metadata_completion.table_memory_count
        )
        total_conflict_field_count = (
            standard_mapping.conflict_field_count
            + stg_standardization.conflict_field_count
            + metadata_completion.conflict_field_key_count
        )
        total_invalid_record_count = (
            standard_mapping.invalid_record_count
            + stg_standardization.invalid_record_count
            + metadata_completion.invalid_field_record_count
            + metadata_completion.invalid_table_record_count
        )
        summary = (
            f"Learning memory contains {total_memory_count} records across "
            "metadata completion, standard mapping, and STG standardization. "
            f"{total_conflict_field_count} field keys have conflicting targets and "
            f"{total_invalid_record_count} invalid records need maintenance. "
            f"Quality-rule learning is {quality_rules.status} with "
            f"{quality_rules.accepted_record_count} accepted review records."
        )
        return LearningHealthOverview(
            standard_mapping=standard_mapping,
            stg_standardization=stg_standardization,
            metadata_completion=metadata_completion,
            quality_rules=quality_rules,
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
            "metadata_completion": metadata_completion_memory_details(),
            "quality_rules": {
                "associations": list(load_quality_rule_associations()),
            },
        }

    def create_backup(self) -> dict[str, object]:
        """Create a timestamped local backup of learning-memory files."""
        return create_learning_memory_backup()

    def list_backups(self) -> list[dict[str, object]]:
        """Return existing learning-memory backups, newest first."""
        return list_learning_memory_backups()

    def prune_invalid(self) -> dict[str, object]:
        """Remove clearly invalid learned-memory records from local CSV stores."""
        standard_mapping = prune_invalid_standard_mapping_memory()
        stg_standardization = prune_invalid_stg_field_memory()
        metadata_completion = prune_invalid_metadata_completion_memory()
        total_removed = (
            int(standard_mapping["removed_count"])
            + int(stg_standardization["removed_count"])
            + int(metadata_completion["removed_count"])
        )
        return {
            "standard_mapping": standard_mapping,
            "stg_standardization": stg_standardization,
            "metadata_completion": metadata_completion,
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
        if normalized_type in {"metadata_completion", "metadata"}:
            result = clear_metadata_completion_memory_by_field_key(field_key)
            result["memory_type"] = "metadata_completion"
            return result
        raise ValueError(
            "memory_type must be one of: standard_mapping, "
            "stg_standardization, metadata_completion"
        )
