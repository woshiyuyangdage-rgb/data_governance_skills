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

    semantic_asset_file = tmp_path / "standard_mapping_semantic.yaml"
    semantic_asset_file.write_text(
        "\n".join(
            [
                "enabled: true",
                "model_name_or_path: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "local_files_only: true",
                "threshold: 0.85",
                "candidate_limit: 3",
                "standard_text_fields:",
                "  - standard_name",
                "  - standard_name_cn",
                "  - description",
                "  - business_domain",
                "  - aliases",
                "source_text_fields:",
                "  - field_name",
                "  - field_name_cn",
                "  - field_description",
            ]
        ),
        encoding="utf-8",
    )

    intent_nlp_asset_file = tmp_path / "intent_nlp_classifier.yaml"
    intent_nlp_asset_file.write_text(
        "\n".join(
            [
                "enabled: true",
                "use_keyword_samples: true",
                "min_similarity: 0.42",
                "min_margin: 0.02",
                "ngram_min: 2",
                "ngram_max: 4",
                "training_examples:",
                "  - intent_name: standard_recommendation",
                "    text: 帮我把这些字段对齐公司统一数据标准",
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
                    },
                    {
                        "asset_name": "standard_mapping_semantic",
                        "asset_type": "yaml",
                        "file_path": str(semantic_asset_file),
                        "description": "Semantic mapping policy config",
                        "editable": True,
                    },
                    {
                        "asset_name": "intent_nlp_classifier",
                        "asset_type": "yaml",
                        "file_path": str(intent_nlp_asset_file),
                        "description": "Local NLP intent classifier config",
                        "editable": True,
                    },
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
                    },
                    {
                        "asset_name": "standard_mapping_semantic",
                        "asset_type": "yaml",
                        "file_path": str(semantic_asset_file),
                        "current_status": "draft",
                        "last_validated_at": None,
                        "last_published_at": None,
                        "last_error_message": None,
                    },
                    {
                        "asset_name": "intent_nlp_classifier",
                        "asset_type": "yaml",
                        "file_path": str(intent_nlp_asset_file),
                        "current_status": "draft",
                        "last_validated_at": None,
                        "last_published_at": None,
                        "last_error_message": None,
                    },
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
