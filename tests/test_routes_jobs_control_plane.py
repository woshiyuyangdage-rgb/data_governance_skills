"""Control-plane route tests."""

from pathlib import Path

from app.api.routes_jobs import (
    ConfigAssetSaveRequest,
    LearningMaintenanceReportExportRequest,
    LearningMemoryClearRequest,
    LearningMemoryRestoreRequest,
    ReviewLearningRebuildRequest,
    backup_then_prune_invalid_learning_memory_route,
    clear_learning_memory_field_key_route,
    create_learning_memory_backup_route,
    export_learning_maintenance_report_route,
    get_config_asset_route,
    learning_health_details_route,
    learning_health_route,
    learning_maintenance_report_route,
    list_learning_memory_backups_route,
    list_config_assets_route,
    prune_invalid_learning_memory_route,
    publish_config_asset_route,
    rebuild_review_learning_route,
    restore_learning_memory_backup_route,
    save_config_asset_route,
    validate_config_asset_route,
    validate_learning_memory_backup_route,
)
from app.api import routes_jobs_control_plane


def test_config_asset_routes_can_list_get_and_validate_assets(
    isolated_control_plane_runtime: Path,
) -> None:
    assets = list_config_assets_route()
    payload = get_config_asset_route("workflow_profiles")
    validation = validate_config_asset_route("workflow_profiles")

    assert assets
    assert assets[0]["asset_name"] == "workflow_profiles"
    assert payload["asset"]["asset_name"] == "workflow_profiles"
    assert validation.is_valid is True


def test_learning_health_route_returns_summary() -> None:
    payload = learning_health_route()

    assert "standard_mapping" in payload
    assert "stg_standardization" in payload
    assert "total_memory_count" in payload
    assert "summary" in payload


def test_learning_health_detail_and_prune_routes(monkeypatch) -> None:
    class FakeLearningHealthService:
        def summarize(self):  # pragma: no cover - not used in this route test
            raise AssertionError("summarize should not be called")

        def details(self):
            return {
                "standard_mapping": {"invalid_records": [{"field_key": "broken"}]},
                "stg_standardization": {"invalid_records": []},
            }

        def maintenance_report(self, backup_limit: int = 3):
            return {
                "health": {"total_memory_count": 3},
                "backup_summary": {"backup_count": 1},
                "recommendations": [],
                "markdown": "# Learning Memory Maintenance Report",
                "backup_limit": backup_limit,
            }

        def export_maintenance_report(
            self,
            *,
            backup_limit: int = 3,
            output_dir: str | None = None,
            base_filename: str | None = None,
        ):
            return {
                "status": "success",
                "json_path": f"{output_dir}/{base_filename}.json",
                "markdown_path": f"{output_dir}/{base_filename}.md",
                "output_dir": str(output_dir),
                "artifact_count": 2,
                "artifacts": [
                    {
                        "format": "json",
                        "path": f"{output_dir}/{base_filename}.json",
                    },
                    {
                        "format": "markdown",
                        "path": f"{output_dir}/{base_filename}.md",
                    },
                ],
                "backup_count": backup_limit,
                "recommendation_count": 1,
                "summary": "Learning-memory maintenance report exported.",
            }

        def prune_invalid(self):
            return {
                "standard_mapping": {"removed_count": 1},
                "stg_standardization": {"removed_count": 0},
                "total_removed_count": 1,
                "summary": "Removed 1 invalid learning-memory records.",
            }

        def backup_then_prune_invalid(self):
            return {
                "status": "success",
                "backup": {"backup_id": "learning_memory_20260605_010203"},
                "prune_result": {"total_removed_count": 1},
                "removed_count": 1,
                "summary": "Created backup before pruning invalid records.",
            }

        def rebuild_review_learning(
            self,
            memory_types=None,
            *,
            create_backup: bool = True,
        ):
            return {
                "status": "success",
                "memory_types": memory_types,
                "backup": (
                    {"backup_id": "learning_memory_20260605_010203"}
                    if create_backup
                    else None
                ),
                "results": {"standard_mapping": {"learned_count": 1}},
                "total_review_record_count": 2,
                "total_learned_count": 1,
            }

        def create_backup(self):
            return {
                "backup_id": "learning_memory_20260605_010203",
                "backed_up_file_count": 2,
                "missing_file_count": 0,
            }

        def list_backups(self):
            return [
                {
                    "backup_id": "learning_memory_20260605_010203",
                    "backed_up_file_count": 2,
                    "missing_file_count": 0,
                }
            ]

        def restore_backup(self, backup_id: str):
            return {
                "backup_id": backup_id,
                "restored_file_count": 2,
                "skipped_file_count": 0,
            }

        def validate_backup(self, backup_id: str):
            return {
                "backup_id": backup_id,
                "is_valid": True,
                "restorable_file_count": 2,
                "issue_count": 0,
            }

        def clear_field_key(self, memory_type: str, field_key: str):
            return {
                "memory_type": memory_type,
                "field_key": field_key,
                "removed_count": 2,
                "status": "cleared",
            }

    monkeypatch.setattr(
        routes_jobs_control_plane,
        "learning_health_service",
        FakeLearningHealthService(),
    )

    details = learning_health_details_route()
    report = learning_maintenance_report_route(backup_limit=1)
    export_result = export_learning_maintenance_report_route(
        LearningMaintenanceReportExportRequest(
            backup_limit=2,
            output_dir="outputs/reports/learning_memory",
            base_filename="route_report",
        )
    )
    backup_result = create_learning_memory_backup_route()
    backups = list_learning_memory_backups_route()
    restore_result = restore_learning_memory_backup_route(
        LearningMemoryRestoreRequest(
            backup_id="learning_memory_20260605_010203",
        )
    )
    validation_result = validate_learning_memory_backup_route(
        LearningMemoryRestoreRequest(
            backup_id="learning_memory_20260605_010203",
        )
    )
    prune_result = prune_invalid_learning_memory_route()
    safe_prune_result = backup_then_prune_invalid_learning_memory_route()
    rebuild_result = rebuild_review_learning_route(
        ReviewLearningRebuildRequest(
            memory_types=["standard_mapping"],
            create_backup=False,
        )
    )
    clear_result = clear_learning_memory_field_key_route(
        LearningMemoryClearRequest(
            memory_type="standard_mapping",
            field_key="buyer_name",
        )
    )

    assert details["standard_mapping"]["invalid_records"][0]["field_key"] == "broken"
    assert report["backup_limit"] == 1
    assert report["backup_summary"]["backup_count"] == 1
    assert export_result["status"] == "success"
    assert export_result["backup_count"] == 2
    assert export_result["artifact_count"] == 2
    assert str(export_result["json_path"]).endswith("route_report.json")
    assert backup_result["backed_up_file_count"] == 2
    assert backups[0]["backup_id"] == "learning_memory_20260605_010203"
    assert restore_result["restored_file_count"] == 2
    assert validation_result["is_valid"] is True
    assert prune_result["total_removed_count"] == 1
    assert safe_prune_result["status"] == "success"
    assert safe_prune_result["removed_count"] == 1
    assert rebuild_result["status"] == "success"
    assert rebuild_result["backup"] is None
    assert rebuild_result["memory_types"] == ["standard_mapping"]
    assert clear_result["status"] == "cleared"
    assert clear_result["field_key"] == "buyer_name"


def test_config_asset_routes_can_save_and_publish_assets(
    isolated_control_plane_runtime: Path,
) -> None:
    save_result = save_config_asset_route(
        "workflow_profiles",
        ConfigAssetSaveRequest(
            content="\n".join(
                [
                    "profiles:",
                    "  - name: metadata_diagnosis_only",
                    "    enabled: true",
                    "    description: Run metadata diagnosis only",
                    "    stages:",
                    "      - diagnosis",
                    "  - name: mapping_only",
                    "    enabled: true",
                    "    description: Run mapping only",
                    "    stages:",
                    "      - mapping",
                ]
            )
        ),
    )
    publish_result = publish_config_asset_route("workflow_profiles")

    assert save_result.status == "draft"
    assert save_result.backup_path is not None
    assert publish_result.status == "published"
