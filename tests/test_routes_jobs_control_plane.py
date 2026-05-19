"""Control-plane route tests."""

from pathlib import Path

from app.api.routes_jobs import (
    ConfigAssetSaveRequest,
    get_config_asset_route,
    list_config_assets_route,
    publish_config_asset_route,
    save_config_asset_route,
    validate_config_asset_route,
)


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
