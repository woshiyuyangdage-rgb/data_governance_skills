"""Lightweight local control plane service for managed governance assets."""

import json
from pathlib import Path
import shutil
from typing import Any

from app.core.control_plane.config_io import (
    detect_asset_format,
    normalize_asset_content,
    read_asset_file,
    write_asset_file,
)
from app.core.control_plane.validators import validate_asset_content
from app.core.knowledge import knowledge_loader
from app.core.models.config_asset import ConfigAsset
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.config_status import ConfigStatus
from app.core.models.validation_result import ValidationResult
from app.core.intent import intent_loader
from app.core.orchestrator import profile_loader
from app.core.rules.config_loader import load_yaml_config
from app.core.tools import tool_loader
from app.core.utils.file_utils import ensure_directory
from app.core.utils.time_utils import utc_now_compact, utc_now_seconds

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTROL_PLANE_DIR = PROJECT_ROOT / "app" / "data" / "control_plane"
ASSET_REGISTRY_PATH = CONTROL_PLANE_DIR / "asset_registry.json"
CONFIG_STATUS_PATH = CONTROL_PLANE_DIR / "config_status.json"
BACKUP_DIR = CONTROL_PLANE_DIR / "backups"
SNAPSHOT_DIR = CONTROL_PLANE_DIR / "snapshots"


def _utc_now() -> str:
    return utc_now_seconds()


class ControlPlaneService:
    """Manage local YAML, JSON, and CSV governance configuration assets."""

    def _ensure_metadata_directories(self) -> None:
        ensure_directory(CONTROL_PLANE_DIR)
        ensure_directory(BACKUP_DIR)
        ensure_directory(SNAPSHOT_DIR)

    def _load_registry(self) -> list[ConfigAsset]:
        self._ensure_metadata_directories()
        payload = json.loads(ASSET_REGISTRY_PATH.read_text(encoding="utf-8"))
        assets = payload.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("asset_registry.json must contain an 'assets' list.")
        return [ConfigAsset.model_validate(asset) for asset in assets]

    def _load_status_map(self) -> dict[str, ConfigStatus]:
        self._ensure_metadata_directories()
        if not CONFIG_STATUS_PATH.exists():
            return {}
        payload = json.loads(CONFIG_STATUS_PATH.read_text(encoding="utf-8"))
        statuses = payload.get("statuses", [])
        if not isinstance(statuses, list):
            raise ValueError("config_status.json must contain a 'statuses' list.")
        return {
            status.asset_name: status
            for status in (ConfigStatus.model_validate(item) for item in statuses)
        }

    def _save_status_map(self, status_map: dict[str, ConfigStatus]) -> None:
        self._ensure_metadata_directories()
        ordered_statuses = sorted(status_map.values(), key=lambda item: item.asset_name)
        CONFIG_STATUS_PATH.write_text(
            json.dumps(
                {"statuses": [status.model_dump() for status in ordered_statuses]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _get_asset(self, asset_name: str) -> ConfigAsset:
        for asset in self._load_registry():
            if asset.asset_name == asset_name:
                return asset
        raise ValueError(f"Managed config asset '{asset_name}' was not found.")

    def _resolve_asset_path(self, asset: ConfigAsset) -> Path:
        raw_path = Path(asset.file_path)
        if raw_path.is_absolute():
            return raw_path
        return PROJECT_ROOT / raw_path

    def _get_status(self, asset: ConfigAsset) -> ConfigStatus:
        status_map = self._load_status_map()
        status = status_map.get(asset.asset_name)
        if status is not None:
            return status
        return ConfigStatus(
            asset_name=asset.asset_name,
            asset_type=asset.asset_type,
            file_path=asset.file_path,
            current_status="draft",
        )

    def _update_status(
        self,
        asset: ConfigAsset,
        *,
        current_status: str,
        validation_result: ValidationResult | None = None,
        last_published_at: str | None = None,
    ) -> ConfigStatus:
        status_map = self._load_status_map()
        existing = status_map.get(asset.asset_name)
        resolved_last_validated_at = (
            _utc_now()
            if validation_result is not None
            else (existing.last_validated_at if existing is not None else None)
        )
        resolved_last_published_at = (
            last_published_at
            if last_published_at is not None
            else (existing.last_published_at if existing is not None else None)
        )
        resolved_last_error_message = (
            "; ".join(validation_result.messages)
            if validation_result is not None and not validation_result.is_valid
            else None
        )
        status = ConfigStatus(
            asset_name=asset.asset_name,
            asset_type=asset.asset_type,
            file_path=asset.file_path,
            current_status=current_status,
            last_validated_at=resolved_last_validated_at,
            last_published_at=resolved_last_published_at,
            last_error_message=resolved_last_error_message,
        )
        status_map[asset.asset_name] = status
        self._save_status_map(status_map)
        return status

    def _invalidate_runtime_caches(self, asset_name: str) -> None:
        if asset_name in {
            "workflow_profiles",
            "intent_patterns",
            "intent_nlp_classifier",
            "tool_registry",
            "quality_rule_templates",
            "quality_rule_policies",
            "execution_package_policies",
            "rule_execution_templates",
            "domain_rule_templates",
            "cross_field_rule_patterns",
            "quality_review_policies",
            "readiness_scoring_policies",
            "governance_gap_taxonomy",
            "remediation_templates",
            "governance_backlog_policies",
            "backlog_status_templates",
            "governance_portfolio_policies",
            "backlog_sla_policies",
            "progress_snapshot_policies",
            "governance_delivery_templates",
            "confirmation_workbook_policies",
            "batch_processing_policies",
            "incremental_rerun_policies",
            "workbook_import_policies",
            "workbook_column_aliases",
            "confirmation_workbook_template_profiles",
            "confirmation_workbook_mapping_specs",
            "confirmation_workbook_diagnosis_policies",
        }:
            load_yaml_config.cache_clear()
        if asset_name == "workflow_profiles":
            profile_loader.load_workflow_profiles.cache_clear()
        elif asset_name == "intent_patterns":
            intent_loader.load_intent_patterns.cache_clear()
            from app.core.intent.intent_nlp_classifier import (
                clear_intent_nlp_classifier_cache,
            )

            clear_intent_nlp_classifier_cache()
        elif asset_name == "intent_nlp_classifier":
            from app.core.intent.intent_nlp_classifier import (
                clear_intent_nlp_classifier_cache,
            )

            clear_intent_nlp_classifier_cache()
        elif asset_name == "tool_registry":
            tool_loader.load_tool_registry.cache_clear()
        elif asset_name in {
            "quality_rule_templates",
            "quality_rule_policies",
            "execution_package_policies",
            "rule_execution_templates",
            "domain_rule_templates",
            "cross_field_rule_patterns",
            "quality_review_policies",
            "readiness_scoring_policies",
            "governance_gap_taxonomy",
            "remediation_templates",
            "governance_backlog_policies",
            "backlog_status_templates",
            "governance_portfolio_policies",
            "backlog_sla_policies",
            "progress_snapshot_policies",
            "governance_delivery_templates",
            "confirmation_workbook_policies",
            "batch_processing_policies",
            "incremental_rerun_policies",
            "workbook_import_policies",
            "workbook_column_aliases",
            "confirmation_workbook_template_profiles",
            "confirmation_workbook_mapping_specs",
            "confirmation_workbook_diagnosis_policies",
        }:
            load_yaml_config.cache_clear()
            if asset_name == "quality_review_policies":
                from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
                    clear_quality_rule_learning_caches,
                )

                clear_quality_rule_learning_caches()
            if asset_name in {
                "confirmation_workbook_template_profiles",
                "confirmation_workbook_mapping_specs",
            }:
                from app.core.delivery import confirmation_template_loader

                confirmation_template_loader.load_confirmation_template_profiles.cache_clear()
                confirmation_template_loader.load_confirmation_template_mapping_specs.cache_clear()
        elif asset_name == "abbreviation_dict":
            knowledge_loader._load_abbreviation_dict_cached.cache_clear()
        elif asset_name == "root_word_dict":
            knowledge_loader._load_root_word_dict_cached.cache_clear()
            from app.core.skills.metadata_diagnosis_skill.naming_standard_check import (
                clear_naming_standard_check_caches,
            )

            clear_naming_standard_check_caches()
        elif asset_name == "standard_fields":
            knowledge_loader._load_standard_fields_cached.cache_clear()
        elif asset_name == "standard_mapping_semantic":
            from app.core.skills.data_standard_mapping_skill import semantic_index

            semantic_index.clear_semantic_mapping_caches()

    def list_assets(self) -> list[ConfigAsset]:
        """Return managed control-plane assets."""
        return self._load_registry()

    def list_assets_with_status(self) -> list[dict[str, object]]:
        """Return managed assets merged with their current status metadata."""
        merged_assets: list[dict[str, object]] = []
        for asset in self.list_assets():
            status = self._get_status(asset)
            merged_assets.append(
                {
                    **asset.model_dump(),
                    **status.model_dump(),
                }
            )
        return merged_assets

    def get_asset_content(self, asset_name: str) -> dict[str, object]:
        """Return content, format, and status for one managed asset."""
        asset = self._get_asset(asset_name)
        resolved_path = self._resolve_asset_path(asset)
        return {
            "asset": asset.model_dump(),
            "status": self._get_status(asset).model_dump(),
            "format": detect_asset_format(resolved_path),
            "content": read_asset_file(resolved_path),
        }

    def validate_asset(self, asset_name: str) -> ValidationResult:
        """Validate one saved asset and persist its validation status."""
        asset = self._get_asset(asset_name)
        content = read_asset_file(self._resolve_asset_path(asset))
        validation_result = validate_asset_content(asset.asset_name, content)
        current_status = (
            "invalid"
            if not validation_result.is_valid
            else (
                "published"
                if self._get_status(asset).current_status == "published"
                else "draft"
            )
        )
        self._update_status(
            asset,
            current_status=current_status,
            validation_result=validation_result,
        )
        return validation_result

    def validate_all_assets(self, *, persist_status: bool = True) -> list[ValidationResult]:
        """Validate every managed asset, optionally persisting validation status."""
        results: list[ValidationResult] = []
        for asset in self.list_assets():
            if persist_status:
                results.append(self.validate_asset(asset.asset_name))
                continue
            content = read_asset_file(self._resolve_asset_path(asset))
            results.append(validate_asset_content(asset.asset_name, content))
        return results

    def validate_asset_preview(self, asset_name: str, content: Any) -> ValidationResult:
        """Validate proposed content without writing it to disk."""
        asset = self._get_asset(asset_name)
        normalized_content = normalize_asset_content(self._resolve_asset_path(asset), content)
        return validate_asset_content(asset.asset_name, normalized_content)

    def create_backup(self, asset_name: str) -> str:
        """Create one local backup copy before overwriting an asset."""
        asset = self._get_asset(asset_name)
        resolved_path = self._resolve_asset_path(asset)
        if not resolved_path.exists():
            raise FileNotFoundError(f"Asset file does not exist: {resolved_path}")

        target_dir = BACKUP_DIR / asset.asset_name
        ensure_directory(target_dir)
        timestamp = utc_now_compact()
        backup_path = target_dir / f"{timestamp}_{resolved_path.name}"
        shutil.copy2(resolved_path, backup_path)
        return str(backup_path)

    def list_asset_backups(self, asset_name: str) -> list[str]:
        """Return saved backup files for one asset, newest first."""
        self._get_asset(asset_name)
        target_dir = BACKUP_DIR / asset_name
        if not target_dir.exists():
            return []
        return [
            str(path)
            for path in sorted(
                target_dir.iterdir(),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            if path.is_file()
        ]

    def save_asset(self, asset_name: str, content: Any) -> ConfigEditResult:
        """Validate, back up, and save one managed asset."""
        asset = self._get_asset(asset_name)
        if not asset.editable:
            return ConfigEditResult(
                asset_name=asset_name,
                status="failed",
                message=f"Asset '{asset_name}' is not editable.",
            )

        resolved_path = self._resolve_asset_path(asset)
        normalized_content = normalize_asset_content(resolved_path, content)
        validation_result = validate_asset_content(asset.asset_name, normalized_content)
        if not validation_result.is_valid:
            self._update_status(
                asset,
                current_status="invalid",
                validation_result=validation_result,
            )
            return ConfigEditResult(
                asset_name=asset_name,
                status="invalid",
                message="Validation failed. Asset content was not saved.",
                validation_result=validation_result,
            )

        backup_path = self.create_backup(asset_name)
        write_asset_file(resolved_path, normalized_content)
        self._invalidate_runtime_caches(asset.asset_name)
        self._update_status(
            asset,
            current_status="draft",
            validation_result=validation_result,
        )
        return ConfigEditResult(
            asset_name=asset_name,
            status="draft",
            message="Asset saved successfully. Status set to draft.",
            backup_path=backup_path,
            validation_result=validation_result,
        )

    def restore_asset_from_backup(
        self,
        asset_name: str,
        backup_path: str | Path,
    ) -> ConfigEditResult:
        """Restore one managed asset from a saved backup copy."""
        asset = self._get_asset(asset_name)
        if not asset.editable:
            return ConfigEditResult(
                asset_name=asset_name,
                status="failed",
                message=f"Asset '{asset_name}' is not editable.",
            )

        resolved_asset_path = self._resolve_asset_path(asset)
        resolved_backup_path = Path(backup_path)
        if not resolved_backup_path.exists():
            raise FileNotFoundError(f"Backup file does not exist: {resolved_backup_path}")

        target_backup_root = BACKUP_DIR / asset.asset_name
        if target_backup_root not in resolved_backup_path.parents:
            raise ValueError(
                f"Backup file must belong to asset '{asset_name}': {resolved_backup_path}"
            )

        backup_content = read_asset_file(resolved_backup_path)
        validation_result = validate_asset_content(asset.asset_name, backup_content)
        if not validation_result.is_valid:
            self._update_status(
                asset,
                current_status="invalid",
                validation_result=validation_result,
            )
            return ConfigEditResult(
                asset_name=asset_name,
                status="invalid",
                message="Backup content is invalid and cannot be restored.",
                validation_result=validation_result,
            )

        current_backup_path = self.create_backup(asset_name)
        write_asset_file(resolved_asset_path, backup_content)
        self._invalidate_runtime_caches(asset.asset_name)
        self._update_status(
            asset,
            current_status="draft",
            validation_result=validation_result,
        )
        return ConfigEditResult(
            asset_name=asset_name,
            status="draft",
            message="Asset restored successfully from backup.",
            backup_path=current_backup_path,
            validation_result=validation_result,
        )

    def publish_asset(self, asset_name: str) -> ConfigEditResult:
        """Mark one validated asset as published."""
        asset = self._get_asset(asset_name)
        validation_result = self.validate_asset(asset_name)
        if not validation_result.is_valid:
            return ConfigEditResult(
                asset_name=asset_name,
                status="invalid",
                message="Asset is invalid and cannot be published.",
                validation_result=validation_result,
            )

        published_at = _utc_now()
        self._update_status(
            asset,
            current_status="published",
            validation_result=validation_result,
            last_published_at=published_at,
        )
        self._invalidate_runtime_caches(asset.asset_name)
        return ConfigEditResult(
            asset_name=asset_name,
            status="published",
            message="Asset published successfully.",
            validation_result=validation_result,
        )


# TODO: extend this service with diff views, snapshot exports, and approval metadata once a real config lifecycle is needed.
