"""Delivery, workbook, and batch request models."""

from pydantic import BaseModel, Field

from app.core.models.workflow_result import WorkflowResult


class GovernanceReadinessAssessmentRequest(BaseModel):
    """Request body for governance readiness assessment."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    apply_review_replay: bool = False


class GovernanceWorkPackageBuildRequest(BaseModel):
    """Request body for building a governance work package."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    apply_review_replay: bool = True
    package_name: str | None = None
    export_package: bool = False
    output_dir: str | None = None
    base_filename: str | None = None


class GovernanceDeliveryPackageRequest(BaseModel):
    """Request body for confirmation workbook and delivery package generation."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    apply_review_replay: bool = True
    output_dir: str | None = None
    base_filename: str | None = None


class BatchGovernanceRequest(BaseModel):
    """Request body for multi-file batch governance."""

    file_paths: list[str] = Field(default_factory=list)
    file_path: str | None = None
    group_by: str = "system_name"
    batch_name: str | None = None
    base_filename: str | None = None


class BatchSnapshotCompareRequest(BaseModel):
    """Request body for comparing local batch snapshots."""

    batch_name: str


class ConfirmationWorkbookImportRequest(BaseModel):
    """Request body for confirmation workbook import."""

    file_path: str
    workbook_type: str = "mapping_confirmation"
    rerun_changed_only: bool = True
