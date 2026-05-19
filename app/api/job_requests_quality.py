"""Review, quality-rule, and execution-package request models."""

from pydantic import BaseModel, Field

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.models.workflow_result import WorkflowResult


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
