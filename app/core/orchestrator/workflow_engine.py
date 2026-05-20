"""Workflow engine for the rule-based P0 governance pipeline."""

from app.core.delivery.delivery_service import DeliveryService
from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.demo_data import build_demo_tables
from app.core.orchestrator.workflow_attachments import WorkflowAttachmentMixin
from app.core.orchestrator.workflow_batch_runners import WorkflowBatchRunnerMixin
from app.core.orchestrator.workflow_confirmation_runners import (
    WorkflowConfirmationRunnerMixin,
)
from app.core.orchestrator.workflow_file_runners import WorkflowFileRunnerMixin
from app.core.orchestrator.workflow_mapping_stg_runners import (
    WorkflowMappingStgRunnerMixin,
)
from app.core.orchestrator.workflow_quality_runners import WorkflowQualityRunnerMixin
from app.core.orchestrator.workflow_template_intake_runners import (
    WorkflowTemplateIntakeRunnerMixin,
)
from app.core.skills.data_quality_rule_skill import QualityRuleRecommendationSkill
from app.core.skills.data_standard_mapping_skill import (
    StandardMappingRecommendationSkill,
)
from app.core.skills.metadata_diagnosis_skill import (
    GovernanceTaskPackagingInput,
    GovernanceTaskPackagingSkill,
    MetadataCompletenessCheckSkill,
    MetadataCompletenessInput,
    MetadataQualityDiagnosisInput,
    MetadataQualityDiagnosisSkill,
    NamingStandardCheckInput,
    NamingStandardCheckSkill,
    TechnicalObjectIdentificationInput,
    TechnicalObjectIdentificationSkill,
)
from app.core.skills.stg_standardization_skill import StgStructureSuggestionSkill


class WorkflowEngine(
    WorkflowFileRunnerMixin,
    WorkflowBatchRunnerMixin,
    WorkflowConfirmationRunnerMixin,
    WorkflowTemplateIntakeRunnerMixin,
    WorkflowMappingStgRunnerMixin,
    WorkflowQualityRunnerMixin,
    WorkflowAttachmentMixin,
):
    """Sequence the five rule-based P0 skills into a stable workflow."""

    def __init__(self) -> None:
        self.metadata_completeness_check = MetadataCompletenessCheckSkill()
        self.technical_object_identification = TechnicalObjectIdentificationSkill()
        self.naming_standard_check = NamingStandardCheckSkill()
        self.metadata_quality_diagnosis = MetadataQualityDiagnosisSkill()
        self.governance_task_packaging = GovernanceTaskPackagingSkill()
        self.standard_mapping_recommendation = StandardMappingRecommendationSkill()
        self.stg_structure_suggestion = StgStructureSuggestionSkill()
        self.quality_rule_recommendation = QualityRuleRecommendationSkill()

    @staticmethod
    def build_demo_tables() -> list[TableMeta]:
        """Expose shared demo data for API, UI, and tests."""
        return build_demo_tables()

    def run(self, payload: list[TableMeta]) -> WorkflowResult:
        """Run the rule-based P0 pipeline."""
        return self.run_p0_pipeline(payload)

    def run_p0_pipeline(self, tables: list[TableMeta]) -> WorkflowResult:
        """Execute the five P0 skills in a fixed sequence."""
        if not tables:
            return WorkflowResult(
                input_table_count=0,
                issue_count=0,
                task_count=0,
                issues=[],
                tasks=[],
                skill_outputs={},
                status="empty",
                message="No tables were provided, so the rule-based P0 pipeline was skipped.",
            )

        completeness_output = self.metadata_completeness_check.run(
            MetadataCompletenessInput(tables=tables)
        )
        technical_output = self.technical_object_identification.run(
            TechnicalObjectIdentificationInput(tables=tables)
        )
        naming_output = self.naming_standard_check.run(
            NamingStandardCheckInput(tables=tables)
        )

        raw_issues = (
            completeness_output.issues
            + technical_output.issues
            + naming_output.issues
        )

        diagnosis_output = self.metadata_quality_diagnosis.run(
            MetadataQualityDiagnosisInput(tables=tables, upstream_issues=raw_issues)
        )

        all_issues = raw_issues + diagnosis_output.issues
        task_output = self.governance_task_packaging.run(
            GovernanceTaskPackagingInput(issues=all_issues)
        )

        skill_outputs = {
            "completeness_output": self._serialize_model(completeness_output),
            "technical_output": self._serialize_model(technical_output),
            "naming_output": self._serialize_model(naming_output),
            "diagnosis_output": self._serialize_model(diagnosis_output),
            "task_output": self._serialize_model(task_output),
        }

        return WorkflowResult(
            input_table_count=len(tables),
            issue_count=len(raw_issues) + len(diagnosis_output.issues),
            task_count=len(task_output.tasks),
            issues=all_issues,
            tasks=task_output.tasks,
            skill_outputs=skill_outputs,
            status="success",
            message=(
                "Rule-based P0 usable version executed successfully across "
                "completeness, technical identification, naming, diagnosis, and task packaging."
            ),
        )

    def run_governance_readiness_assessment(
        self,
        tables: list[TableMeta],
        apply_review: bool = False,
    ) -> WorkflowResult:
        """Run readiness assessment on top of the quality/package chain."""
        result = (
            self.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package(tables)
            if apply_review
            else self.run_p0_plus_mapping_plus_stg_plus_quality_with_package(tables)
        )
        return self._attach_governance_readiness(
            result,
            package_name=(
                "governance_readiness_assessment_with_review"
                if apply_review
                else "governance_readiness_assessment"
            ),
        )

    def run_full_governance_work_package_with_backlog(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run the full work-package workflow and attach governance backlog items."""
        result = self.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_and_readiness(
            tables
        )
        return self._attach_governance_backlog(result)

    def run_confirmation_workbook_only(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run the delivery chain and export confirmation workbooks only."""
        result = self.run_full_governance_work_package_with_backlog(tables)
        workbook_results = DeliveryService().build_confirmation_workbooks(
            result,
            base_name="confirmation_workbook_only",
        )
        result.confirmation_workbook_results = workbook_results
        if result.status == "success":
            result.message = (
                f"{result.message} Confirmation workbooks were also generated."
            )
        return result

    def run_full_governance_delivery_package(
        self,
        tables: list[TableMeta],
        apply_review: bool = True,
    ) -> WorkflowResult:
        """Run the governance chain through backlog and attach delivery artifacts."""
        result = self.run_governance_backlog_build(
            tables,
            apply_review=apply_review,
        )
        return self._attach_governance_delivery_package(
            result,
            package_name=(
                "governance_delivery_package_with_review"
                if apply_review
                else "governance_delivery_package"
            ),
        )

    def run_governance_backlog_build(
        self,
        tables: list[TableMeta],
        apply_review: bool = False,
    ) -> WorkflowResult:
        """Run readiness/remediation and build backlog items."""
        result = self.run_governance_readiness_assessment(
            tables,
            apply_review=apply_review,
        )
        return self._attach_governance_backlog(result)

    def run_governance_portfolio_assessment(
        self,
        tables: list[TableMeta],
        apply_review: bool = False,
    ) -> WorkflowResult:
        """Run backlog build and attach SLA, portfolio, and snapshot outputs."""
        result = self.run_governance_backlog_build(
            tables,
            apply_review=apply_review,
        )
        return self._attach_governance_portfolio(result)

    def run_full_governance_backlog_with_portfolio(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run the full governance backlog package and attach portfolio outputs."""
        result = self.run_full_governance_work_package_with_backlog(tables)
        return self._attach_governance_portfolio(result)
