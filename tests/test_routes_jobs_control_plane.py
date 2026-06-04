"""Control-plane route tests."""

from pathlib import Path

from app.api.routes_jobs import (
    ConfigAssetSaveRequest,
    LearningMemoryClearRequest,
    clear_learning_memory_field_key_route,
    get_config_asset_route,
    learning_health_details_route,
    learning_health_route,
    list_config_assets_route,
    prune_invalid_learning_memory_route,
    publish_config_asset_route,
    save_config_asset_route,
    validate_config_asset_route,
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

        def prune_invalid(self):
            return {
                "standard_mapping": {"removed_count": 1},
                "stg_standardization": {"removed_count": 0},
                "total_removed_count": 1,
                "summary": "Removed 1 invalid learning-memory records.",
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
    prune_result = prune_invalid_learning_memory_route()
    clear_result = clear_learning_memory_field_key_route(
        LearningMemoryClearRequest(
            memory_type="standard_mapping",
            field_key="buyer_name",
        )
    )

    assert details["standard_mapping"]["invalid_records"][0]["field_key"] == "broken"
    assert prune_result["total_removed_count"] == 1
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
