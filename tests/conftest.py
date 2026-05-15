"""Test fixtures for Windows-safe local temporary paths."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / ".pytest_runtime"


def _runtime_root() -> Path:
    DEFAULT_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    return DEFAULT_RUNTIME_ROOT


@pytest.fixture
def tmp_path(request) -> Path:
    """Provide a writable test temp path without relying on the system temp root."""
    safe_name = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_"
        for character in request.node.name
    )
    path = _runtime_root() / f"{safe_name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def isolated_control_plane_runtime(tmp_path: Path, monkeypatch) -> Path:
    """Redirect control-plane status writes to a per-test runtime directory."""
    from app.core.control_plane import control_plane_service as control_plane_module

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
