"""Tests for the local governance control plane service."""

import json
from pathlib import Path

from app.core.control_plane import control_plane_service as control_plane_module
from app.core.control_plane.control_plane_service import ControlPlaneService


def _setup_control_plane_runtime(tmp_path: Path, monkeypatch) -> Path:
    asset_file = tmp_path / "workflow_profiles.yaml"
    asset_file.write_text(
        "\n".join(
            [
                "profiles:",
                "  - name: metadata_diagnosis_only",
                "    enabled: true",
                "    description: Run metadata diagnosis only",
                "    stages:",
                "      - diagnosis",
            ]
        ),
        encoding="utf-8",
    )

    asset_registry_path = tmp_path / "asset_registry.json"
    asset_registry_path.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "asset_name": "workflow_profiles",
                        "asset_type": "yaml",
                        "file_path": str(asset_file),
                        "description": "Workflow profile config",
                        "editable": True,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    config_status_path = tmp_path / "config_status.json"
    config_status_path.write_text(
        json.dumps(
            {
                "statuses": [
                    {
                        "asset_name": "workflow_profiles",
                        "asset_type": "yaml",
                        "file_path": str(asset_file),
                        "current_status": "published",
                        "last_validated_at": None,
                        "last_published_at": None,
                        "last_error_message": None,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(control_plane_module, "CONTROL_PLANE_DIR", tmp_path)
    monkeypatch.setattr(control_plane_module, "ASSET_REGISTRY_PATH", asset_registry_path)
    monkeypatch.setattr(control_plane_module, "CONFIG_STATUS_PATH", config_status_path)
    monkeypatch.setattr(control_plane_module, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(control_plane_module, "SNAPSHOT_DIR", tmp_path / "snapshots")
    return asset_file


def test_control_plane_service_can_list_and_get_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _setup_control_plane_runtime(tmp_path, monkeypatch)
    service = ControlPlaneService()

    assets = service.list_assets()
    payload = service.get_asset_content("workflow_profiles")

    assert assets
    assert assets[0].asset_name == "workflow_profiles"
    assert payload["format"] == "yaml"
    assert payload["content"]["profiles"][0]["name"] == "metadata_diagnosis_only"


def test_control_plane_service_can_validate_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _setup_control_plane_runtime(tmp_path, monkeypatch)
    service = ControlPlaneService()

    result = service.validate_asset("workflow_profiles")

    assert result.is_valid is True
    status_payload = json.loads(
        control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    )
    assert status_payload["statuses"][0]["current_status"] == "published"


def test_control_plane_service_save_creates_backup_and_marks_draft(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _setup_control_plane_runtime(tmp_path, monkeypatch)
    service = ControlPlaneService()

    edited_content = "\n".join(
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
    result = service.save_asset("workflow_profiles", edited_content)

    assert result.status == "draft"
    assert result.validation_result is not None
    assert result.validation_result.is_valid is True
    assert result.backup_path is not None
    assert Path(result.backup_path).exists()

    status_payload = json.loads(
        control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    )
    assert status_payload["statuses"][0]["current_status"] == "draft"


def test_control_plane_service_publish_updates_status(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _setup_control_plane_runtime(tmp_path, monkeypatch)
    service = ControlPlaneService()

    result = service.publish_asset("workflow_profiles")

    assert result.status == "published"
    assert result.validation_result is not None
    assert result.validation_result.is_valid is True

    status_payload = json.loads(
        control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    )
    assert status_payload["statuses"][0]["current_status"] == "published"
    assert status_payload["statuses"][0]["last_published_at"] is not None
