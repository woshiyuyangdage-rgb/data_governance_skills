"""Tests for learned-memory health service."""

import json

from app.core.learning import learning_health_service
from app.core.learning.learning_health_service import LearningHealthService
from app.core.parser.metadata_learning import MetadataCompletionMemoryHealth
from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
    QualityRuleLearningHealth,
)
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
    monkeypatch.setattr(
        learning_health_service,
        "summarize_metadata_completion_memory",
        lambda: MetadataCompletionMemoryHealth(
            field_memory_count=5,
            table_memory_count=2,
            field_key_count=4,
            table_key_count=2,
            conflict_field_key_count=1,
            conflict_table_key_count=1,
            invalid_field_record_count=2,
            invalid_table_record_count=1,
            conflict_field_keys=("buyer_name",),
            conflict_table_keys=("customer_master",),
            invalid_field_record_keys=("customer_master:broken_field",),
            invalid_table_record_keys=("broken_table",),
        ),
    )
    monkeypatch.setattr(
        learning_health_service,
        "summarize_quality_rule_learning",
        lambda: QualityRuleLearningHealth(
            enabled=True,
            dependency_available=True,
            accepted_record_count=6,
            min_records=3,
            association_rule_count=2,
            learned_rule_types=("not_null", "numeric_range"),
            status="active",
        ),
    )

    overview = LearningHealthService().summarize()
    payload = overview.model_dump()

    assert overview.total_memory_count == 14
    assert overview.total_conflict_field_count == 3
    assert overview.total_invalid_record_count == 4
    assert "14 records" in overview.summary
    assert "Quality-rule learning is active" in overview.summary
    assert payload["standard_mapping"]["memory_count"] == 3
    assert payload["stg_standardization"]["memory_count"] == 4
    assert payload["metadata_completion"]["field_memory_count"] == 5
    assert payload["quality_rules"]["association_rule_count"] == 2


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
        "metadata_completion_memory_details",
        lambda: {
            "field_conflict_records": [{"field_key": "buyer_name"}],
            "table_conflict_records": [],
            "invalid_field_records": [{"field_key": "broken_field"}],
            "invalid_table_records": [{"table_key": "broken_table"}],
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "load_quality_rule_associations",
        lambda: ({"rule_type": "not_null"},),
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
    monkeypatch.setattr(
        learning_health_service,
        "prune_invalid_metadata_completion_memory",
        lambda: {
            "field_memory": {"removed_count": 1},
            "table_memory": {"removed_count": 0},
            "removed_count": 1,
            "summary": "Removed 1 invalid metadata completion records.",
        },
    )

    service = LearningHealthService()
    details = service.details()
    prune_result = service.prune_invalid()

    assert details["standard_mapping"]["conflict_records"][0]["field_key"] == "buyer_name"
    assert details["stg_standardization"]["generic_records"][0]["field_key"] == "type"
    assert details["metadata_completion"]["invalid_table_records"][0]["table_key"] == "broken_table"
    assert details["quality_rules"]["associations"][0]["rule_type"] == "not_null"
    assert prune_result["metadata_completion"]["removed_count"] == 1
    assert prune_result["total_removed_count"] == 4
    assert "Removed 4" in prune_result["summary"]


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
    monkeypatch.setattr(
        learning_health_service,
        "clear_metadata_completion_memory_by_field_key",
        lambda field_key: {
            "field_key": field_key,
            "removed_count": 3,
            "status": "cleared",
        },
    )

    service = LearningHealthService()
    mapping_result = service.clear_field_key("standard_mapping", "buyer_name")
    stg_result = service.clear_field_key("stg_standardization", "buyer_name")
    metadata_result = service.clear_field_key("metadata_completion", "buyer_name")

    assert mapping_result["memory_type"] == "standard_mapping"
    assert mapping_result["removed_count"] == 2
    assert stg_result["memory_type"] == "stg_standardization"
    assert stg_result["removed_count"] == 1
    assert metadata_result["memory_type"] == "metadata_completion"
    assert metadata_result["removed_count"] == 3


def test_learning_health_service_creates_and_lists_backups(monkeypatch) -> None:
    monkeypatch.setattr(
        learning_health_service,
        "create_learning_memory_backup",
        lambda: {
            "backup_id": "learning_memory_20260605_010203",
            "backed_up_file_count": 3,
            "missing_file_count": 1,
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "list_learning_memory_backups",
        lambda: [
            {
                "backup_id": "learning_memory_20260605_010203",
                "backed_up_file_count": 3,
                "missing_file_count": 1,
            }
        ],
    )
    monkeypatch.setattr(
        learning_health_service,
        "restore_learning_memory_backup",
        lambda backup_id: {
            "backup_id": backup_id,
            "restored_file_count": 2,
            "skipped_file_count": 0,
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "validate_learning_memory_backup",
        lambda backup_id: {
            "backup_id": backup_id,
            "is_valid": True,
            "restorable_file_count": 2,
            "issue_count": 0,
        },
    )

    service = LearningHealthService()
    backup = service.create_backup()
    backups = service.list_backups()
    restore_result = service.restore_backup("learning_memory_20260605_010203")
    validation = service.validate_backup("learning_memory_20260605_010203")

    assert backup["backup_id"] == "learning_memory_20260605_010203"
    assert backup["backed_up_file_count"] == 3
    assert backups[0]["missing_file_count"] == 1
    assert restore_result["restored_file_count"] == 2
    assert validation["is_valid"] is True


def test_learning_health_service_builds_maintenance_report(monkeypatch) -> None:
    monkeypatch.setattr(
        learning_health_service,
        "summarize_standard_mapping_memory",
        lambda: StandardMappingMemoryHealth(
            memory_count=3,
            conflict_field_count=1,
            invalid_record_count=1,
        ),
    )
    monkeypatch.setattr(
        learning_health_service,
        "summarize_stg_field_memory",
        lambda: StgMemoryHealth(memory_count=2),
    )
    monkeypatch.setattr(
        learning_health_service,
        "summarize_metadata_completion_memory",
        lambda: MetadataCompletionMemoryHealth(
            field_memory_count=2,
            table_memory_count=1,
        ),
    )
    monkeypatch.setattr(
        learning_health_service,
        "summarize_quality_rule_learning",
        lambda: QualityRuleLearningHealth(
            enabled=True,
            dependency_available=True,
            accepted_record_count=2,
            min_records=3,
            status="insufficient_records",
        ),
    )
    monkeypatch.setattr(
        learning_health_service,
        "standard_mapping_memory_details",
        lambda: {
            "conflict_records": [{"field_key": "buyer_name"}],
            "generic_records": [],
            "invalid_records": [{"field_key": "broken_mapping"}],
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "stg_field_memory_details",
        lambda: {
            "conflict_records": [],
            "generic_records": [],
            "invalid_records": [],
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "metadata_completion_memory_details",
        lambda: {
            "field_conflict_records": [],
            "table_conflict_records": [],
            "invalid_field_records": [],
            "invalid_table_records": [],
        },
    )
    monkeypatch.setattr(
        learning_health_service,
        "load_quality_rule_associations",
        lambda: (),
    )
    monkeypatch.setattr(
        learning_health_service,
        "list_learning_memory_backups",
        lambda: [{"backup_id": "learning_memory_20260605_010203"}],
    )
    monkeypatch.setattr(
        learning_health_service,
        "validate_learning_memory_backup",
        lambda backup_id: {
            "backup_id": backup_id,
            "is_valid": True,
            "issue_count": 0,
            "restorable_file_count": 2,
            "restorable_files": [
                {"restore_action": "overwrite"},
                {"restore_action": "no_change"},
            ],
        },
    )

    report = LearningHealthService().maintenance_report()

    actions = {item["action"] for item in report["recommendations"]}
    assert report["health"]["total_memory_count"] == 8
    assert report["detail_counts"]["standard_mapping"]["invalid_record_count"] == 1
    assert report["backup_summary"]["latest_restore_action_counts"]["overwrite"] == 1
    assert "backup_then_prune_invalid_learning_memory" in actions
    assert "review_restore_overwrite_plan" in actions
    assert "Learning Memory Maintenance Report" in report["markdown"]


def test_learning_health_service_exports_maintenance_report(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_maintenance_report(
        self,
        backup_limit: int = 3,
    ) -> dict[str, object]:
        assert backup_limit == 5
        return {
            "generated_at": "2026-06-08T00:00:00Z",
            "health": {"total_memory_count": 3},
            "detail_counts": {},
            "backup_summary": {"backup_count": 2},
            "recommendations": [{"action": "review_conflicting_learning_keys"}],
            "markdown": "# Learning Memory Maintenance Report\n\n- Total memory records: 3",
        }

    monkeypatch.setattr(
        LearningHealthService,
        "maintenance_report",
        fake_maintenance_report,
    )

    result = LearningHealthService().export_maintenance_report(
        backup_limit=5,
        output_dir=tmp_path,
        base_filename="learning_report",
    )

    json_path = tmp_path / "learning_report.json"
    markdown_path = tmp_path / "learning_report.md"
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert result["json_path"] == str(json_path)
    assert result["markdown_path"] == str(markdown_path)
    assert result["output_dir"] == str(tmp_path)
    assert result["artifact_count"] == 2
    assert {artifact["format"] for artifact in result["artifacts"]} == {
        "json",
        "markdown",
    }
    assert all(int(artifact["size_bytes"]) > 0 for artifact in result["artifacts"])
    assert all(len(str(artifact["sha256"])) == 64 for artifact in result["artifacts"])
    assert result["backup_count"] == 2
    assert result["recommendation_count"] == 1
    assert payload["health"]["total_memory_count"] == 3
    assert "Learning Memory Maintenance Report" in markdown_path.read_text(
        encoding="utf-8"
    )


def test_learning_health_service_backs_up_before_pruning_invalid(
    monkeypatch,
) -> None:
    calls: list[str] = []
    health_payloads = iter(
        [
            {"total_invalid_record_count": 2, "total_memory_count": 8},
            {"total_invalid_record_count": 0, "total_memory_count": 6},
        ]
    )

    class FakeHealthOverview:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def model_dump(self) -> dict[str, object]:
            return self.payload

    def fake_summarize(self) -> FakeHealthOverview:
        calls.append("summarize")
        return FakeHealthOverview(next(health_payloads))

    def fake_create_backup(self) -> dict[str, object]:
        calls.append("backup")
        return {"backup_id": "learning_memory_20260608_010203"}

    def fake_prune_invalid(self) -> dict[str, object]:
        calls.append("prune")
        return {
            "total_removed_count": 2,
            "summary": "Removed 2 invalid learning-memory records.",
        }

    monkeypatch.setattr(LearningHealthService, "summarize", fake_summarize)
    monkeypatch.setattr(LearningHealthService, "create_backup", fake_create_backup)
    monkeypatch.setattr(LearningHealthService, "prune_invalid", fake_prune_invalid)

    result = LearningHealthService().backup_then_prune_invalid()

    assert calls == ["summarize", "backup", "prune", "summarize"]
    assert result["status"] == "success"
    assert result["removed_count"] == 2
    assert result["backup"]["backup_id"] == "learning_memory_20260608_010203"
    assert result["before_health"]["total_invalid_record_count"] == 2
    assert result["after_health"]["total_invalid_record_count"] == 0
    assert "Created backup learning_memory_20260608_010203" in result["summary"]


def test_learning_health_service_rejects_unknown_memory_type() -> None:
    service = LearningHealthService()

    try:
        service.clear_field_key("unknown", "buyer_name")
    except ValueError as exc:
        assert "memory_type must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown memory_type")
