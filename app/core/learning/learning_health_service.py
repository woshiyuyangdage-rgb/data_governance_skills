"""Facade for learned-memory health summaries."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from app.core.learning.learning_memory_backup import (
    create_learning_memory_backup,
    list_learning_memory_backups,
    restore_learning_memory_backup,
    validate_learning_memory_backup,
)
from app.core.parser.metadata_learning import (
    MetadataCompletionMemoryHealth,
    clear_metadata_completion_memory_by_field_key,
    metadata_completion_memory_details,
    prune_invalid_metadata_completion_memory,
    summarize_metadata_completion_memory,
)
from app.core.review.override_store import load_mapping_overrides, load_stg_overrides
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
    QualityRuleLearningHealth,
    clear_quality_rule_learning_caches,
    load_quality_rule_associations,
    summarize_quality_rule_learning,
)
from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    StandardMappingMemoryHealth,
    clear_standard_mapping_memory_by_field_key,
    learn_standard_mapping_memory_from_review_records,
    prune_invalid_standard_mapping_memory,
    standard_mapping_memory_details,
    summarize_standard_mapping_memory,
)
from app.core.skills.stg_standardization_skill.stg_learning import (
    StgMemoryHealth,
    clear_stg_field_memory_by_field_key,
    learn_stg_memory_from_review_records,
    prune_invalid_stg_field_memory,
    stg_field_memory_details,
    summarize_stg_field_memory,
)
from app.core.utils.file_utils import (
    ensure_directory,
    resolve_allowed_local_path,
    sanitize_filename,
)
from app.core.utils.time_utils import utc_now_compact, utc_now_seconds

DEFAULT_LEARNING_REPORT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[3] / "outputs" / "reports" / "learning_memory"
)
REVIEW_LEARNING_MEMORY_TYPES = (
    "standard_mapping",
    "stg_standardization",
    "quality_rules",
)
REVIEW_LEARNING_MEMORY_TYPE_ALIASES = {
    "mapping": "standard_mapping",
    "standard_mapping": "standard_mapping",
    "data_standard_mapping": "standard_mapping",
    "stg": "stg_standardization",
    "stg_standardization": "stg_standardization",
    "quality": "quality_rules",
    "quality_rule": "quality_rules",
    "quality_rules": "quality_rules",
    "data_quality_rule": "quality_rules",
}


def _record_count(section: dict[str, object], key: str) -> int:
    records = section.get(key, [])
    return len(records) if isinstance(records, list) else 0


def _restore_action_counts(validation: dict[str, object] | None) -> dict[str, int]:
    counts = {"create": 0, "overwrite": 0, "no_change": 0}
    if not validation:
        return counts
    for item in validation.get("restorable_files", []):
        if not isinstance(item, dict):
            continue
        action = str(item.get("restore_action") or "")
        if action in counts:
            counts[action] += 1
    return counts


def _file_artifact(path: Path, artifact_format: str) -> dict[str, object]:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "format": artifact_format,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _normalize_review_learning_memory_types(
    memory_types: list[str] | tuple[str, ...] | None,
) -> list[str]:
    if not memory_types:
        return list(REVIEW_LEARNING_MEMORY_TYPES)

    normalized: list[str] = []
    invalid_types: list[str] = []
    for raw_type in memory_types:
        key = str(raw_type or "").strip().lower()
        resolved = REVIEW_LEARNING_MEMORY_TYPE_ALIASES.get(key)
        if resolved is None:
            invalid_types.append(str(raw_type))
            continue
        if resolved not in normalized:
            normalized.append(resolved)

    if invalid_types:
        raise ValueError(
            "memory_types must contain only: "
            f"{', '.join(REVIEW_LEARNING_MEMORY_TYPES)}. "
            f"Invalid values: {', '.join(invalid_types)}"
        )
    return normalized


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

    def maintenance_report(self, backup_limit: int = 3) -> dict[str, object]:
        """Return a consolidated maintenance report for local learning memory."""
        health = self.summarize().model_dump()
        details = self.details()
        backups = self.list_backups()
        recent_backups = backups[: max(0, int(backup_limit))]
        backup_validations: list[dict[str, object]] = []
        for backup in recent_backups:
            backup_id = str(backup.get("backup_id") or "")
            if not backup_id:
                continue
            try:
                validation = self.validate_backup(backup_id)
            except Exception as exc:
                validation = {
                    "backup_id": backup_id,
                    "is_valid": False,
                    "issue_count": 1,
                    "issues": [{"reason": "validation_failed", "detail": str(exc)}],
                    "restorable_file_count": 0,
                }
            backup_validations.append(validation)

        detail_counts = {
            "standard_mapping": {
                "conflict_record_count": _record_count(details["standard_mapping"], "conflict_records"),
                "generic_record_count": _record_count(details["standard_mapping"], "generic_records"),
                "invalid_record_count": _record_count(details["standard_mapping"], "invalid_records"),
            },
            "stg_standardization": {
                "conflict_record_count": _record_count(details["stg_standardization"], "conflict_records"),
                "generic_record_count": _record_count(details["stg_standardization"], "generic_records"),
                "invalid_record_count": _record_count(details["stg_standardization"], "invalid_records"),
            },
            "metadata_completion": {
                "field_conflict_record_count": _record_count(details["metadata_completion"], "field_conflict_records"),
                "table_conflict_record_count": _record_count(details["metadata_completion"], "table_conflict_records"),
                "invalid_field_record_count": _record_count(details["metadata_completion"], "invalid_field_records"),
                "invalid_table_record_count": _record_count(details["metadata_completion"], "invalid_table_records"),
            },
            "quality_rules": {
                "association_count": _record_count(details["quality_rules"], "associations"),
            },
        }

        latest_validation = backup_validations[0] if backup_validations else None
        restore_action_counts = _restore_action_counts(latest_validation)
        recommendations: list[dict[str, object]] = []
        if not backups:
            recommendations.append(
                {
                    "priority": "high",
                    "action": "create_learning_memory_backup",
                    "reason": "No learning-memory backup package is available.",
                }
            )
        if int(health["total_invalid_record_count"]) > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "action": "backup_then_prune_invalid_learning_memory",
                    "reason": "Invalid learned-memory records can pollute future recommendations.",
                }
            )
        if int(health["total_conflict_field_count"]) > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "action": "review_conflicting_learning_keys",
                    "reason": "Conflicting learned targets should be reviewed before broad reuse.",
                }
            )
        if latest_validation and not bool(latest_validation.get("is_valid")):
            recommendations.append(
                {
                    "priority": "medium",
                    "action": "inspect_latest_backup_validation_issues",
                    "reason": "The latest backup has validation issues and should not be restored blindly.",
                }
            )
        if restore_action_counts["overwrite"] > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "action": "review_restore_overwrite_plan",
                    "reason": f"Latest backup restore would overwrite {restore_action_counts['overwrite']} files.",
                }
            )
        quality_status = str(health["quality_rules"].get("status") or "")
        if quality_status in {"dependency_unavailable", "insufficient_records", "no_associations"}:
            recommendations.append(
                {
                    "priority": "low",
                    "action": "improve_quality_rule_learning_inputs",
                    "reason": f"Quality-rule learning status is {quality_status}.",
                }
            )

        recommendation_lines = [
            f"- [{item['priority']}] {item['action']}: {item['reason']}"
            for item in recommendations
        ] or ["- No immediate maintenance action is required."]
        markdown = "\n".join(
            [
                "# Learning Memory Maintenance Report",
                "",
                f"- Generated at: {utc_now_seconds()}",
                f"- Total memory records: {health['total_memory_count']}",
                f"- Conflict field keys: {health['total_conflict_field_count']}",
                f"- Invalid records: {health['total_invalid_record_count']}",
                f"- Backups available: {len(backups)}",
                f"- Latest backup valid: {latest_validation.get('is_valid') if latest_validation else 'N/A'}",
                f"- Latest restore actions: create={restore_action_counts['create']}, overwrite={restore_action_counts['overwrite']}, no_change={restore_action_counts['no_change']}",
                "",
                "## Recommended Actions",
                *recommendation_lines,
            ]
        )

        return {
            "generated_at": utc_now_seconds(),
            "health": health,
            "detail_counts": detail_counts,
            "backup_summary": {
                "backup_count": len(backups),
                "recent_backups": recent_backups,
                "recent_backup_validations": backup_validations,
                "latest_restore_action_counts": restore_action_counts,
            },
            "recommendations": recommendations,
            "markdown": markdown,
        }

    def export_maintenance_report(
        self,
        *,
        backup_limit: int = 3,
        output_dir: str | Path | None = None,
        base_filename: str | None = None,
    ) -> dict[str, object]:
        """Export the consolidated maintenance report as JSON and Markdown."""
        report = self.maintenance_report(backup_limit=backup_limit)
        target_dir = resolve_allowed_local_path(
            output_dir or DEFAULT_LEARNING_REPORT_OUTPUT_DIR,
            path_label="output_dir",
        )
        ensure_directory(target_dir)
        safe_name = sanitize_filename(
            base_filename or f"learning_memory_maintenance_{utc_now_compact()}"
        )
        json_path = target_dir / f"{safe_name}.json"
        markdown_path = target_dir / f"{safe_name}.md"
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(str(report["markdown"]), encoding="utf-8")
        artifacts = [
            _file_artifact(json_path, "json"),
            _file_artifact(markdown_path, "markdown"),
        ]
        return {
            "status": "success",
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "output_dir": str(target_dir),
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "backup_count": report["backup_summary"]["backup_count"],
            "recommendation_count": len(report["recommendations"]),
            "summary": "Learning-memory maintenance report exported.",
        }

    def create_backup(self) -> dict[str, object]:
        """Create a timestamped local backup of learning-memory files."""
        return create_learning_memory_backup()

    def list_backups(self) -> list[dict[str, object]]:
        """Return existing learning-memory backups, newest first."""
        return list_learning_memory_backups()

    def restore_backup(self, backup_id: str) -> dict[str, object]:
        """Restore learning-memory files from one local backup package."""
        return restore_learning_memory_backup(backup_id)

    def validate_backup(self, backup_id: str) -> dict[str, object]:
        """Validate one local learning-memory backup package."""
        return validate_learning_memory_backup(backup_id)

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

    def backup_then_prune_invalid(self) -> dict[str, object]:
        """Create a backup before pruning invalid learned-memory records."""
        before_health = self.summarize().model_dump()
        backup = self.create_backup()
        prune_result = self.prune_invalid()
        after_health = self.summarize().model_dump()
        removed_count = int(prune_result.get("total_removed_count") or 0)
        backup_id = str(backup.get("backup_id") or "N/A")
        return {
            "status": "success",
            "backup": backup,
            "prune_result": prune_result,
            "before_health": before_health,
            "after_health": after_health,
            "removed_count": removed_count,
            "summary": (
                f"Created backup {backup_id} before pruning; removed "
                f"{removed_count} invalid learning-memory records."
            ),
        }

    def rebuild_review_learning(
        self,
        memory_types: list[str] | tuple[str, ...] | None = None,
        *,
        create_backup: bool = True,
    ) -> dict[str, object]:
        """Rebuild learned memory from locally saved human review records."""
        selected_types = _normalize_review_learning_memory_types(memory_types)
        backup = self.create_backup() if create_backup else None
        results: dict[str, dict[str, object]] = {}

        if "standard_mapping" in selected_types:
            records = load_mapping_overrides()
            learning_summary = learn_standard_mapping_memory_from_review_records(records)
            results["standard_mapping"] = {
                "status": "success",
                "review_record_count": len(records),
                "learned_count": learning_summary.learned_count,
                "memory_count": learning_summary.memory_count,
                "learning_memory_path": learning_summary.output_path,
            }

        if "stg_standardization" in selected_types:
            records = load_stg_overrides()
            learning_summary = learn_stg_memory_from_review_records(records)
            results["stg_standardization"] = {
                "status": "success",
                "review_record_count": len(records),
                "learned_count": learning_summary.learned_count,
                "memory_count": learning_summary.memory_count,
                "learning_memory_path": learning_summary.output_path,
            }

        if "quality_rules" in selected_types:
            records = load_quality_rule_overrides()
            clear_quality_rule_learning_caches()
            associations = tuple(load_quality_rule_associations())
            health = summarize_quality_rule_learning(
                records=records,
                associations=associations,
            )
            results["quality_rules"] = {
                "status": health.status,
                "review_record_count": len(records),
                "accepted_record_count": health.accepted_record_count,
                "association_rule_count": health.association_rule_count,
                "learned_rule_types": list(health.learned_rule_types),
                "dependency_available": health.dependency_available,
                "enabled": health.enabled,
            }

        total_review_record_count = sum(
            int(result.get("review_record_count") or 0)
            for result in results.values()
        )
        total_learned_count = sum(
            int(result.get("learned_count") or 0)
            + int(result.get("association_rule_count") or 0)
            for result in results.values()
        )
        return {
            "status": "success",
            "memory_types": selected_types,
            "backup": backup,
            "results": results,
            "total_review_record_count": total_review_record_count,
            "total_learned_count": total_learned_count,
            "summary": (
                "Rebuilt review-based learning memory for "
                f"{', '.join(selected_types)} from {total_review_record_count} "
                f"review records; produced {total_learned_count} learned signals."
            ),
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
