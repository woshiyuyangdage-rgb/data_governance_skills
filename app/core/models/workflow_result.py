"""Workflow result model for the local governance workflow."""

from typing import Any

from pydantic import BaseModel, Field

from app.core.models.batch_group_result import BatchGroupResult
from app.core.models.batch_run_result import BatchRunResult
from app.core.models.backlog_summary import BacklogSummary
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.confirmation_roundtrip_result import ConfirmationRoundTripResult
from app.core.models.confirmation_template_match_result import ConfirmationTemplateMatchResult
from app.core.models.confirmation_template_mapping_result import (
    ConfirmationTemplateMappingResult,
)
from app.core.models.confirmation_workbook_result import ConfirmationWorkbookResult
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.ai_ready_score import AiReadyScore
from app.core.models.domain_pack_match_result import DomainPackMatchResult
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_delivery_manifest import GovernanceDeliveryManifest
from app.core.models.governance_delivery_package_result import (
    GovernanceDeliveryPackageResult,
)
from app.core.models.governance_portfolio_summary import GovernancePortfolioSummary
from app.core.models.governance_task import GovernanceTask
from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.incremental_diff_item import IncrementalDiffItem
from app.core.models.incremental_diff_summary import IncrementalDiffSummary
from app.core.models.intake_match_result import IntakeMatchResult
from app.core.models.intake_mapping_result import IntakeMappingResult
from app.core.models.intake_normalization_result import IntakeNormalizationResult
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult, UnmappedField
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.progress_snapshot import ProgressSnapshot
from app.core.models.project_template_run_result import ProjectTemplateRunResult
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.models.rule_export_result import RuleExportResult
from app.core.models.review_summary import ReviewSummary
from app.core.models.semantic_enrichment_result import (
    FieldDescriptionSuggestion,
    TableSemanticSummary,
)
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_table_suggestion import StgTableSuggestion
from app.core.models.workbook_import_summary import WorkbookImportSummary


class WorkflowResult(BaseModel):
    """Unified workflow result returned by the orchestration layer."""

    input_table_count: int = 0
    issue_count: int = 0
    task_count: int = 0
    issues: list[Issue] = Field(default_factory=list)
    tasks: list[GovernanceTask] = Field(default_factory=list)
    field_description_suggestions: list[FieldDescriptionSuggestion] = Field(
        default_factory=list
    )
    table_semantic_summaries: list[TableSemanticSummary] = Field(default_factory=list)
    semantic_enrichment_summary: str | None = None
    mapping_results: list[MappingResult] = Field(default_factory=list)
    confirmed_mapping_results: list[MappingResult] = Field(default_factory=list)
    unmapped_fields: list[UnmappedField] = Field(default_factory=list)
    mapping_summary: str | None = None
    stg_suggestions: list[StgTableSuggestion] = Field(default_factory=list)
    stg_field_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    confirmed_stg_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    stg_summary: str | None = None
    quality_rule_suggestions: list[QualityRuleSuggestion] = Field(default_factory=list)
    cross_field_quality_rules: list[CrossFieldQualityRule] = Field(default_factory=list)
    quality_rule_packages: list[QualityRulePackage] = Field(default_factory=list)
    quality_rule_summary: str | None = None
    confirmed_quality_rules: list[ConfirmedQualityRule] = Field(default_factory=list)
    quality_rule_review_summary: dict[str, Any] = Field(default_factory=dict)
    quality_review_queue_summary: dict[str, Any] = Field(default_factory=dict)
    rule_export_results: list[RuleExportResult] = Field(default_factory=list)
    execution_ready_package: ExecutionReadyPackage | None = None
    execution_package_summary: dict[str, Any] = Field(default_factory=dict)
    execution_package_export_results: list[ExecutionPackageExportResult] = Field(
        default_factory=list
    )
    readiness_scores: list[ReadinessScore] = Field(default_factory=list)
    governance_gaps: list[GovernanceGap] = Field(default_factory=list)
    remediation_actions: list[RemediationAction] = Field(default_factory=list)
    governance_work_package: GovernanceWorkPackage | None = None
    readiness_summary: dict[str, Any] = Field(default_factory=dict)
    ai_ready_scores: list[AiReadyScore] = Field(default_factory=list)
    ai_ready_summary: dict[str, Any] = Field(default_factory=dict)
    governance_backlog_items: list[GovernanceBacklogItem] = Field(default_factory=list)
    backlog_summary: BacklogSummary | None = None
    backlog_sla_statuses: list[BacklogSlaStatus] = Field(default_factory=list)
    governance_portfolio_summary: GovernancePortfolioSummary | None = None
    progress_snapshot: ProgressSnapshot | None = None
    confirmation_workbook_results: list[ConfirmationWorkbookResult] = Field(
        default_factory=list
    )
    governance_delivery_manifest: GovernanceDeliveryManifest | None = None
    governance_delivery_package_result: GovernanceDeliveryPackageResult | None = None
    batch_run_result: BatchRunResult | None = None
    batch_group_results: list[BatchGroupResult] = Field(default_factory=list)
    incremental_diff_items: list[IncrementalDiffItem] = Field(default_factory=list)
    incremental_diff_summary: IncrementalDiffSummary | None = None
    rerun_scope_summary: dict[str, Any] = Field(default_factory=dict)
    workbook_import_summaries: list[WorkbookImportSummary] = Field(default_factory=list)
    roundtrip_results: list[ConfirmationRoundTripResult] = Field(default_factory=list)
    roundtrip_changed_objects_summary: dict[str, Any] = Field(default_factory=dict)
    domain_pack_match: DomainPackMatchResult | None = None
    project_template_result: ProjectTemplateRunResult | None = None
    intake_match_result: IntakeMatchResult | None = None
    intake_mapping_result: IntakeMappingResult | None = None
    intake_normalization_result: IntakeNormalizationResult | None = None
    confirmation_template_match_result: ConfirmationTemplateMatchResult | None = None
    confirmation_template_mapping_result: ConfirmationTemplateMappingResult | None = None
    review_summary: ReviewSummary | None = None
    skill_outputs: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    message: str = ""
