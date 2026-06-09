"""Control-plane request models."""

from pydantic import BaseModel


class ConfigAssetSaveRequest(BaseModel):
    """Request body for saving one managed config asset."""

    content: object


class LearningMemoryClearRequest(BaseModel):
    """Request body for clearing learned memory by field key."""

    memory_type: str
    field_key: str


class LearningMemoryRestoreRequest(BaseModel):
    """Request body for restoring learned memory from a backup package."""

    backup_id: str


class LearningMaintenanceReportExportRequest(BaseModel):
    """Request body for exporting learning-memory maintenance reports."""

    backup_limit: int = 3
    output_dir: str | None = None
    base_filename: str | None = None
