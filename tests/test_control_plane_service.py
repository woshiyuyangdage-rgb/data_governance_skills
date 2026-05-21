"""Tests for the local governance control plane service."""

import json
from pathlib import Path

from app.core.control_plane import control_plane_service as control_plane_module
from app.core.control_plane.control_plane_service import ControlPlaneService


def test_control_plane_service_can_list_and_get_assets(
    isolated_control_plane_runtime: Path,
) -> None:
    service = ControlPlaneService()

    assets = service.list_assets()
    payload = service.get_asset_content("workflow_profiles")

    assert assets
    assert assets[0].asset_name == "workflow_profiles"
    assert any(asset.asset_name == "standard_mapping_semantic" for asset in assets)
    assert any(asset.asset_name == "intent_nlp_classifier" for asset in assets)
    assert payload["format"] == "yaml"
    assert payload["content"]["profiles"][0]["name"] == "metadata_diagnosis_only"


def test_control_plane_service_can_validate_assets(
    isolated_control_plane_runtime: Path,
) -> None:
    service = ControlPlaneService()

    result = service.validate_asset("workflow_profiles")

    assert result.is_valid is True
    status_payload = json.loads(
        control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    )
    workflow_status = next(
        status
        for status in status_payload["statuses"]
        if status["asset_name"] == "workflow_profiles"
    )
    assert workflow_status["current_status"] == "published"


def test_control_plane_service_can_validate_all_assets_without_status_writes(
    isolated_control_plane_runtime: Path,
) -> None:
    before_status = control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    service = ControlPlaneService()

    results = service.validate_all_assets(persist_status=False)

    after_status = control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    assert len(results) == 3
    assert results[0].asset_name == "workflow_profiles"
    assert results[0].is_valid is True
    assert any(result.asset_name == "standard_mapping_semantic" for result in results)
    assert any(result.asset_name == "intent_nlp_classifier" for result in results)
    assert after_status == before_status


def test_control_plane_service_can_validate_semantic_mapping_asset(
    isolated_control_plane_runtime: Path,
) -> None:
    service = ControlPlaneService()

    result = service.validate_asset("standard_mapping_semantic")

    assert result.is_valid is True


def test_control_plane_service_can_validate_intent_nlp_classifier_asset(
    isolated_control_plane_runtime: Path,
) -> None:
    service = ControlPlaneService()

    result = service.validate_asset("intent_nlp_classifier")

    assert result.is_valid is True


def test_control_plane_service_save_creates_backup_and_marks_draft(
    isolated_control_plane_runtime: Path,
) -> None:
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
    isolated_control_plane_runtime: Path,
) -> None:
    service = ControlPlaneService()

    result = service.publish_asset("workflow_profiles")

    assert result.status == "published"
    assert result.validation_result is not None
    assert result.validation_result.is_valid is True

    status_payload = json.loads(
        control_plane_module.CONFIG_STATUS_PATH.read_text(encoding="utf-8")
    )
    workflow_status = next(
        status
        for status in status_payload["statuses"]
        if status["asset_name"] == "workflow_profiles"
    )
    assert workflow_status["current_status"] == "published"
    assert workflow_status["last_published_at"] is not None
