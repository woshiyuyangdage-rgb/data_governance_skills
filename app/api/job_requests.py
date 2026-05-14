"""Request models for governance job routes."""

from pydantic import BaseModel, Field

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.models.workflow_result import WorkflowResult


class FileRunRequest(BaseModel):
    """Request body for running the pipeline from a local file."""

    file_path: str


class DomainPackMatchRequest(BaseModel):
    """Request body for matching a domain governance pack."""

    text: str


class ProjectTemplateRunRequest(BaseModel):
    """Request body for running a project template."""

    template_name: str
    file_path: str
    domain_pack_name: str | None = None
    output_dir: str | None = None


class MetadataIntakeRequest(BaseModel):
    """Request body for metadata intake diagnosis and normalization."""

    file_path: str
    intake_profile_name: str | None = None
    sheet_name: str | None = None
    profile_name: str = "metadata_diagnosis_only"


class ConfirmationTemplateRequest(BaseModel):
    """Request body for template-aware confirmation workbook import."""

    file_path: str
    workbook_type: str | None = None
    confirmation_template_name: str | None = None
    sheet_name: str | None = None
    rerun_changed_only: bool = True


class MappingReviewSaveRequest(BaseModel):
    """Request body for saving mapping review records."""

    records: list[MappingReviewRecord]


class StgReviewSaveRequest(BaseModel):
    """Request body for saving STG review records."""

    records: list[StgReviewRecord]


class QualityRuleReviewRequest(BaseModel):
    """Request body for reviewing quality rule suggestions."""

    quality_rule_suggestions: list[QualityRuleSuggestion] = Field(default_factory=list)
    cross_field_quality_rules: list[CrossFieldQualityRule] = Field(default_factory=list)
    workflow_result: WorkflowResult | None = None
    review_inputs: dict[str, dict[str, str | None]] = Field(default_factory=dict)
    records: list[QualityRuleReviewRecord] = Field(default_factory=list)
    save_overrides: bool = False
    source: str = "api"


class ConfirmedQualityRuleExportRequest(BaseModel):
    """Request body for exporting confirmed quality rules."""

    export_format: str = "json"
    confirmed_quality_rules: list[ConfirmedQualityRule] = Field(default_factory=list)
    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    apply_review_replay: bool = True
    output_dir: str | None = None
    base_filename: str | None = None


class ExecutionPackageBuildRequest(BaseModel):
    """Request body for building an execution-ready governance package."""

    confirmed_quality_rules: list[ConfirmedQualityRule] = Field(default_factory=list)
    workflow_result: WorkflowResult | None = None
    execution_ready_package: ExecutionReadyPackage | None = None
    file_path: str | None = None
    apply_review_replay: bool = True
    profile_name: str | None = None


class ExecutionPackageExportRequest(BaseModel):
    """Request body for exporting an execution-ready governance package."""

    export_format: str = "json"
    execution_ready_package: ExecutionReadyPackage | None = None
    confirmed_quality_rules: list[ConfirmedQualityRule] = Field(default_factory=list)
    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    apply_review_replay: bool = True
    output_dir: str | None = None
    base_filename: str | None = None
    profile_name: str | None = None


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


class GovernanceBacklogBuildRequest(BaseModel):
    """Request body for building local governance backlog items."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    remediation_actions: list[dict[str, object]] = Field(default_factory=list)
    apply_review_replay: bool = True
    persist: bool = False
    append: bool = True


class GovernanceBacklogStatusUpdateRequest(BaseModel):
    """Request body for backlog status update."""

    new_status: str
    note: str | None = None


class GovernancePortfolioAssessmentRequest(BaseModel):
    """Request body for governance portfolio assessment."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    governance_backlog_items: list[dict[str, object]] = Field(default_factory=list)
    backlog_sla_statuses: list[dict[str, object]] = Field(default_factory=list)
    apply_review_replay: bool = True
    notes: str | None = None


class ProgressSnapshotRequest(BaseModel):
    """Request body for governance progress snapshot generation."""

    workflow_result: WorkflowResult | None = None
    file_path: str | None = None
    governance_backlog_items: list[dict[str, object]] = Field(default_factory=list)
    backlog_sla_statuses: list[dict[str, object]] = Field(default_factory=list)
    apply_review_replay: bool = True
    notes: str | None = None
    save: bool = False


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


class IntentTextRequest(BaseModel):
    """Request body for interpreting a natural-language governance task."""

    text: str
    file_path: str | None = None


class AgentShellPlanRequest(BaseModel):
    """Request body for agent shell plan preview."""

    text: str
    file_path: str | None = None
    session_id: str | None = None


class AgentShellRunRequest(BaseModel):
    """Request body for agent shell confirm-and-run flow."""

    text: str
    file_path: str | None = None
    session_id: str | None = None
    force_run: bool = False


class ConfigAssetSaveRequest(BaseModel):
    """Request body for saving one managed config asset."""

    content: object


class NativeToolInvokeRequest(BaseModel):
    """Request body for adapter-layer native tool invocation."""

    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)


class OpenAIToolInvokeRequest(BaseModel):
    """Request body for adapter-layer OpenAI-style invocation."""

    function_name: str
    arguments_json: str | dict[str, object] | None = None
