"""Control-plane config asset job routes."""

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    ConfigAssetSaveRequest,
    LearningMaintenanceReportExportRequest,
    LearningMemoryClearRequest,
    LearningMemoryRestoreRequest,
)
from app.core.control_plane.control_plane_service import ControlPlaneService
from app.core.learning.learning_health_service import LearningHealthService
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.validation_result import ValidationResult

router = APIRouter()
control_plane_service = ControlPlaneService()
learning_health_service = LearningHealthService()


@router.get("/config-assets", response_model=list[dict[str, object]])
def list_config_assets_route() -> list[dict[str, object]]:
    """Return managed control-plane assets with their current status."""
    return control_plane_service.list_assets_with_status()


@router.get("/learning-health", response_model=dict[str, object])
def learning_health_route() -> dict[str, object]:
    """Return local learning-memory health summary."""
    return learning_health_service.summarize().model_dump()


@router.get("/learning-health/details", response_model=dict[str, object])
def learning_health_details_route() -> dict[str, object]:
    """Return learned-memory records that need maintenance attention."""
    return learning_health_service.details()


@router.get("/learning-health/report", response_model=dict[str, object])
def learning_maintenance_report_route(
    backup_limit: int = 3,
) -> dict[str, object]:
    """Return a consolidated learning-memory maintenance report."""
    return learning_health_service.maintenance_report(backup_limit=backup_limit)


@router.post("/learning-health/report/export", response_model=dict[str, object])
def export_learning_maintenance_report_route(
    payload: LearningMaintenanceReportExportRequest,
) -> dict[str, object]:
    """Export the learning-memory maintenance report as JSON and Markdown."""
    try:
        return learning_health_service.export_maintenance_report(
            backup_limit=payload.backup_limit,
            output_dir=payload.output_dir,
            base_filename=payload.base_filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/learning-health/backups", response_model=dict[str, object])
def create_learning_memory_backup_route() -> dict[str, object]:
    """Create a timestamped backup package for local learning-memory files."""
    return learning_health_service.create_backup()


@router.get("/learning-health/backups", response_model=list[dict[str, object]])
def list_learning_memory_backups_route() -> list[dict[str, object]]:
    """Return local learning-memory backup packages, newest first."""
    return learning_health_service.list_backups()


@router.post("/learning-health/backups/restore", response_model=dict[str, object])
def restore_learning_memory_backup_route(
    payload: LearningMemoryRestoreRequest,
) -> dict[str, object]:
    """Restore local learning-memory files from one backup package."""
    try:
        return learning_health_service.restore_backup(payload.backup_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/learning-health/backups/validate", response_model=dict[str, object])
def validate_learning_memory_backup_route(
    payload: LearningMemoryRestoreRequest,
) -> dict[str, object]:
    """Validate one local learning-memory backup package before restore."""
    try:
        return learning_health_service.validate_backup(payload.backup_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/learning-health/prune-invalid", response_model=dict[str, object])
def prune_invalid_learning_memory_route() -> dict[str, object]:
    """Remove clearly invalid learned-memory records from local stores."""
    return learning_health_service.prune_invalid()


@router.post(
    "/learning-health/backup-then-prune-invalid",
    response_model=dict[str, object],
)
def backup_then_prune_invalid_learning_memory_route() -> dict[str, object]:
    """Create a backup before removing invalid learned-memory records."""
    return learning_health_service.backup_then_prune_invalid()


@router.post("/learning-health/clear-field-key", response_model=dict[str, object])
def clear_learning_memory_field_key_route(
    payload: LearningMemoryClearRequest,
) -> dict[str, object]:
    """Clear learned-memory records for one field key in one memory domain."""
    try:
        return learning_health_service.clear_field_key(
            payload.memory_type,
            payload.field_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/config-assets/{asset_name}", response_model=dict[str, object])
def get_config_asset_route(asset_name: str) -> dict[str, object]:
    """Return one managed config asset with current content and status."""
    try:
        return control_plane_service.get_asset_content(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/validate",
    response_model=ValidationResult,
)
def validate_config_asset_route(asset_name: str) -> ValidationResult:
    """Validate one managed config asset."""
    try:
        return control_plane_service.validate_asset(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/save",
    response_model=ConfigEditResult,
)
def save_config_asset_route(
    asset_name: str,
    payload: ConfigAssetSaveRequest,
) -> ConfigEditResult:
    """Save one managed config asset after validation."""
    try:
        return control_plane_service.save_asset(asset_name, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/publish",
    response_model=ConfigEditResult,
)
def publish_config_asset_route(asset_name: str) -> ConfigEditResult:
    """Publish one managed config asset after validation."""
    try:
        return control_plane_service.publish_asset(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
