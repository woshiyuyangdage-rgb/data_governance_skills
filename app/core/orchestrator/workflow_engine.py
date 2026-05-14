"""Workflow engine for the rule-based P0 governance pipeline."""

from app.core.delivery.delivery_service import DeliveryService
from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.delivery.confirmation_roundtrip_service import ConfirmationRoundTripService
from app.core.governance.roundtrip_rerun_service import RoundTripRerunService
from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.review.override_store import load_mapping_overrides, load_stg_overrides
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.review.quality_batch_review_service import summarize_review_queue
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    summarize_quality_rule_review_records,
)
from app.core.review.review_service import summarize_review_records
from app.core.orchestrator.demo_data import build_demo_tables
from app.core.orchestrator.workflow_attachments import WorkflowAttachmentMixin
from app.core.orchestrator.workflow_batch_runners import WorkflowBatchRunnerMixin
from app.core.orchestrator.workflow_file_runners import WorkflowFileRunnerMixin
from app.core.skills.governance_task_packaging import (
    GovernanceTaskPackagingInput,
    GovernanceTaskPackagingSkill,
)
from app.core.skills.metadata_completeness_check import (
    MetadataCompletenessCheckSkill,
    MetadataCompletenessInput,
)
from app.core.skills.metadata_quality_diagnosis import (
    MetadataQualityDiagnosisInput,
    MetadataQualityDiagnosisSkill,
)
from app.core.skills.naming_standard_check import (
    NamingStandardCheckInput,
    NamingStandardCheckSkill,
)
from app.core.skills.quality_rule_recommendation import (
    QualityRuleRecommendationInput,
    QualityRuleRecommendationSkill,
)
from app.core.skills.standard_mapping_recommendation import (
    StandardMappingInput,
    StandardMappingRecommendationSkill,
)
from app.core.skills.stg_structure_suggestion import (
    StgStructureSuggestionInput,
    StgStructureSuggestionSkill,
)
from app.core.skills.technical_object_identification import (
    TechnicalObjectIdentificationInput,
    TechnicalObjectIdentificationSkill,
)


class WorkflowEngine(
    WorkflowFileRunnerMixin,
    WorkflowBatchRunnerMixin,
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

    def run_project_template(
        self,
        template_name: str,
        file_path: str,
        domain_pack_name: str | None = None,
        output_dir: str | None = None,
    ) -> WorkflowResult:
        """Run a project template through the existing workflow stack."""
        service = __import__(
            "app.core.templates.project_template_service",
            fromlist=["ProjectTemplateService"],
        ).ProjectTemplateService()
        return service.run_project_template(
            template_name=template_name,
            file_path=file_path,
            domain_pack_name=domain_pack_name,
            output_dir=output_dir,
        )

    def run_project_template_batch(
        self,
        template_name: str,
        file_paths: list[str],
        domain_pack_name: str | None = None,
        output_dir: str | None = None,
    ) -> list[WorkflowResult]:
        """Run one project template against multiple files."""
        return [
            self.run_project_template(
                template_name=template_name,
                file_path=file_path,
                domain_pack_name=domain_pack_name,
                output_dir=output_dir,
            )
            for file_path in file_paths
        ]

    def run_governance_with_intake_profile(
        self,
        file_path: str,
        profile_name: str = "metadata_diagnosis_only",
        intake_profile_name: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkflowResult:
        """Normalize metadata intake first, then run an existing table-based workflow."""
        service = __import__(
            "app.core.intake.intake_adapter_service",
            fromlist=["IntakeAdapterService"],
        ).IntakeAdapterService()
        tables, match_result, normalization = service.load_tables(
            file_path,
            profile_name=intake_profile_name,
            sheet_name=sheet_name,
        )
        if normalization.status != "success":
            return WorkflowResult(
                status="failed",
                message=normalization.message or "Metadata intake normalization failed.",
                intake_match_result=match_result,
                intake_mapping_result=normalization.mapping_result,
                intake_normalization_result=normalization,
            )

        handlers = {
            "metadata_diagnosis_only": self.run_p0_pipeline,
            "diagnosis_plus_mapping": self.run_p0_plus_mapping,
            "diagnosis_mapping_stg": self.run_p0_plus_mapping_plus_stg,
            "diagnosis_mapping_stg_with_review": self.run_p0_plus_mapping_plus_stg_with_review,
            "diagnosis_mapping_stg_quality": self.run_p0_plus_mapping_plus_stg_plus_quality,
            "diagnosis_mapping_stg_quality_with_review": self.run_p0_plus_mapping_plus_stg_plus_quality_with_review,
            "diagnosis_mapping_stg_quality_package": self.run_p0_plus_mapping_plus_stg_plus_quality_with_package,
            "diagnosis_mapping_stg_quality_package_with_review": self.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package,
            "governance_delivery_package_with_review": self.run_full_governance_delivery_package,
            "mapping_only": self.run_standard_mapping,
            "stg_only_from_mapping": self.run_stg_only_from_mapping,
            "quality_only_from_stg": self.run_quality_only_from_stg,
            "quality_only_from_stg_with_review": self.run_quality_only_from_stg_with_review,
        }
        handler = handlers.get(profile_name)
        if handler is None:
            return WorkflowResult(
                status="failed",
                message=f"Workflow profile '{profile_name}' is not supported by intake-aware execution.",
                intake_match_result=match_result,
                intake_mapping_result=normalization.mapping_result,
                intake_normalization_result=normalization,
            )

        result = handler(tables)
        result.intake_match_result = match_result
        result.intake_mapping_result = normalization.mapping_result
        result.intake_normalization_result = normalization
        result.skill_outputs = {
            **dict(result.skill_outputs),
            "intake_normalization_output": normalization.model_dump(),
        }
        return result

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

    def run_standard_mapping(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run only the P1 standard mapping recommendation skill."""
        mapping_output = self.standard_mapping_recommendation.run(
            StandardMappingInput(tables=tables, apply_overrides=False)
        )
        return WorkflowResult(
            input_table_count=len(tables),
            issue_count=len(mapping_output.issues),
            task_count=0,
            issues=mapping_output.issues,
            tasks=[],
            mapping_results=mapping_output.mapping_results,
            confirmed_mapping_results=[],
            unmapped_fields=mapping_output.unmapped_fields,
            mapping_summary=mapping_output.summary,
            skill_outputs={
                "standard_mapping_output": self._serialize_model(mapping_output),
            },
            status="success" if tables else "empty",
            message=(
                "Rule-based standard mapping recommendation executed successfully."
                if tables
                else "No tables were provided, so standard mapping was skipped."
            ),
        )

    def run_stg_only_from_mapping(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run naming enhancement, mapping, and STG suggestion without full diagnosis packaging."""
        if not tables:
            return WorkflowResult(
                input_table_count=0,
                issue_count=0,
                task_count=0,
                issues=[],
                tasks=[],
                mapping_results=[],
                unmapped_fields=[],
                stg_suggestions=[],
                stg_field_suggestions=[],
                skill_outputs={},
                status="empty",
                message=(
                    "No tables were provided, so mapping and STG structure suggestion were skipped."
                ),
            )

        naming_output = self.naming_standard_check.run(
            NamingStandardCheckInput(tables=tables)
        )
        mapping_output = self.standard_mapping_recommendation.run(
            StandardMappingInput(tables=tables, apply_overrides=False)
        )
        stg_output = self.stg_structure_suggestion.run(
            StgStructureSuggestionInput(
                tables=tables,
                mapping_results=mapping_output.mapping_results,
                naming_field_suggestions=naming_output.field_name_suggestions,
                apply_overrides=False,
            )
        )

        return WorkflowResult(
            input_table_count=len(tables),
            issue_count=len(mapping_output.issues) + len(stg_output.issues),
            task_count=0,
            issues=mapping_output.issues + stg_output.issues,
            tasks=[],
            mapping_results=mapping_output.mapping_results,
            confirmed_mapping_results=[],
            unmapped_fields=mapping_output.unmapped_fields,
            mapping_summary=mapping_output.summary,
            stg_suggestions=stg_output.stg_table_suggestions,
            stg_field_suggestions=stg_output.field_suggestions_flat,
            confirmed_stg_suggestions=[],
            stg_summary=stg_output.summary,
            skill_outputs={
                "naming_output": self._serialize_model(naming_output),
                "standard_mapping_output": self._serialize_model(mapping_output),
                "stg_structure_output": self._serialize_model(stg_output),
            },
            status="success",
            message=(
                "Rule-based mapping and STG structure suggestion executed successfully "
                "without full diagnosis packaging."
            ),
        )

    def run_p0_plus_mapping(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run the existing P0 pipeline and then append P1 mapping recommendations."""
        p0_result = self.run_p0_pipeline(tables)
        mapping_output = self.standard_mapping_recommendation.run(
            StandardMappingInput(tables=tables, apply_overrides=False)
        )

        merged_skill_outputs = dict(p0_result.skill_outputs)
        merged_skill_outputs["standard_mapping_output"] = self._serialize_model(
            mapping_output
        )

        status = p0_result.status
        message = p0_result.message
        if tables and p0_result.status == "success":
            message += " Standard mapping recommendations were also generated."

        return WorkflowResult(
            input_table_count=p0_result.input_table_count,
            issue_count=p0_result.issue_count + len(mapping_output.issues),
            task_count=p0_result.task_count,
            issues=p0_result.issues + mapping_output.issues,
            tasks=p0_result.tasks,
            mapping_results=mapping_output.mapping_results,
            confirmed_mapping_results=[],
            unmapped_fields=mapping_output.unmapped_fields,
            mapping_summary=mapping_output.summary,
            skill_outputs=merged_skill_outputs,
            status=status,
            message=message,
        )

    def run_p0_plus_mapping_with_review(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run P0 plus mapping and apply saved human review overrides."""
        p0_result = self.run_p0_pipeline(tables)
        mapping_overrides = load_mapping_overrides()
        mapping_output = self.standard_mapping_recommendation.run(
            StandardMappingInput(
                tables=tables,
                apply_overrides=True,
                override_records=mapping_overrides,
            )
        )

        merged_skill_outputs = dict(p0_result.skill_outputs)
        merged_skill_outputs["standard_mapping_output"] = self._serialize_model(
            mapping_output
        )
        review_summary = summarize_review_records(mapping_overrides, [])

        message = p0_result.message
        if tables and p0_result.status == "success":
            message += " Standard mapping overrides were also applied."

        return WorkflowResult(
            input_table_count=p0_result.input_table_count,
            issue_count=p0_result.issue_count + len(mapping_output.issues),
            task_count=p0_result.task_count,
            issues=p0_result.issues + mapping_output.issues,
            tasks=p0_result.tasks,
            mapping_results=mapping_output.mapping_results,
            confirmed_mapping_results=mapping_output.confirmed_mapping_results,
            unmapped_fields=mapping_output.unmapped_fields,
            mapping_summary=mapping_output.summary,
            review_summary=review_summary,
            skill_outputs=merged_skill_outputs,
            status=p0_result.status,
            message=message,
        )

    def run_p0_plus_mapping_plus_stg(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run the P0 pipeline, standard mapping, and STG structure suggestion."""
        mapping_result = self.run_p0_plus_mapping(tables)
        naming_output = mapping_result.skill_outputs.get("naming_output", {})
        naming_field_suggestions = (
            naming_output.get("field_name_suggestions", {})
            if isinstance(naming_output, dict)
            else {}
        )

        stg_output = self.stg_structure_suggestion.run(
            StgStructureSuggestionInput(
                tables=tables,
                mapping_results=mapping_result.mapping_results,
                naming_field_suggestions=naming_field_suggestions,
                apply_overrides=False,
            )
        )

        merged_skill_outputs = dict(mapping_result.skill_outputs)
        merged_skill_outputs["stg_structure_output"] = self._serialize_model(stg_output)

        message = mapping_result.message
        if tables and mapping_result.status == "success":
            message += " STG structure suggestions were also generated."

        return WorkflowResult(
            input_table_count=mapping_result.input_table_count,
            issue_count=mapping_result.issue_count + len(stg_output.issues),
            task_count=mapping_result.task_count,
            issues=mapping_result.issues + stg_output.issues,
            tasks=mapping_result.tasks,
            mapping_results=mapping_result.mapping_results,
            confirmed_mapping_results=[],
            unmapped_fields=mapping_result.unmapped_fields,
            mapping_summary=mapping_result.mapping_summary,
            stg_suggestions=stg_output.stg_table_suggestions,
            stg_field_suggestions=stg_output.field_suggestions_flat,
            confirmed_stg_suggestions=[],
            stg_summary=stg_output.summary,
            skill_outputs=merged_skill_outputs,
            status=mapping_result.status,
            message=message,
        )

    def run_p0_plus_mapping_plus_stg_with_review(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run P0, mapping, and STG generation with saved review overrides applied."""
        mapping_result = self.run_p0_plus_mapping_with_review(tables)
        naming_output = mapping_result.skill_outputs.get("naming_output", {})
        naming_field_suggestions = (
            naming_output.get("field_name_suggestions", {})
            if isinstance(naming_output, dict)
            else {}
        )
        stg_overrides = load_stg_overrides()
        effective_mapping_results = (
            mapping_result.confirmed_mapping_results or mapping_result.mapping_results
        )
        stg_output = self.stg_structure_suggestion.run(
            StgStructureSuggestionInput(
                tables=tables,
                mapping_results=effective_mapping_results,
                naming_field_suggestions=naming_field_suggestions,
                apply_overrides=True,
                override_records=stg_overrides,
            )
        )

        merged_skill_outputs = dict(mapping_result.skill_outputs)
        merged_skill_outputs["stg_structure_output"] = self._serialize_model(stg_output)
        review_summary = summarize_review_records(
            load_mapping_overrides(),
            stg_overrides,
        )

        message = mapping_result.message
        if tables and mapping_result.status == "success":
            message += " STG review overrides were also applied."

        return WorkflowResult(
            input_table_count=mapping_result.input_table_count,
            issue_count=mapping_result.issue_count + len(stg_output.issues),
            task_count=mapping_result.task_count,
            issues=mapping_result.issues + stg_output.issues,
            tasks=mapping_result.tasks,
            mapping_results=mapping_result.mapping_results,
            confirmed_mapping_results=mapping_result.confirmed_mapping_results,
            unmapped_fields=mapping_result.unmapped_fields,
            mapping_summary=mapping_result.mapping_summary,
            stg_suggestions=stg_output.stg_table_suggestions,
            stg_field_suggestions=stg_output.field_suggestions_flat,
            confirmed_stg_suggestions=stg_output.confirmed_stg_suggestions,
            stg_summary=stg_output.summary,
            review_summary=review_summary,
            skill_outputs=merged_skill_outputs,
            status=mapping_result.status,
            message=message,
        )

    def run_quality_only_from_stg(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run mapping, STG suggestion, and quality rule recommendation without full diagnosis packaging."""
        stg_result = self.run_stg_only_from_mapping(tables)
        quality_output = self.quality_rule_recommendation.run(
            QualityRuleRecommendationInput(
                tables=tables,
                mapping_results=stg_result.mapping_results,
                stg_suggestions=stg_result.stg_field_suggestions,
            )
        )

        merged_skill_outputs = dict(stg_result.skill_outputs)
        merged_skill_outputs["quality_rule_output"] = self._serialize_model(quality_output)
        review_queue_summary = summarize_review_queue(
            list(quality_output.quality_rule_suggestions)
            + [
                QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
                for rule in quality_output.cross_field_quality_rules
            ]
        )
        message = stg_result.message
        if tables and stg_result.status == "success":
            message += " Quality rule recommendations were also generated."

        return WorkflowResult(
            input_table_count=stg_result.input_table_count,
            issue_count=stg_result.issue_count + len(quality_output.issues),
            task_count=stg_result.task_count,
            issues=stg_result.issues + quality_output.issues,
            tasks=stg_result.tasks,
            mapping_results=stg_result.mapping_results,
            confirmed_mapping_results=stg_result.confirmed_mapping_results,
            unmapped_fields=stg_result.unmapped_fields,
            mapping_summary=stg_result.mapping_summary,
            stg_suggestions=stg_result.stg_suggestions,
            stg_field_suggestions=stg_result.stg_field_suggestions,
            confirmed_stg_suggestions=stg_result.confirmed_stg_suggestions,
            stg_summary=stg_result.stg_summary,
            quality_rule_suggestions=quality_output.quality_rule_suggestions,
            cross_field_quality_rules=quality_output.cross_field_quality_rules,
            quality_rule_packages=quality_output.quality_rule_packages,
            quality_rule_summary=quality_output.summary,
            quality_review_queue_summary=review_queue_summary,
            skill_outputs=merged_skill_outputs,
            status=stg_result.status,
            message=message,
        )

    def run_p0_plus_mapping_plus_stg_plus_quality(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run diagnosis, mapping, STG suggestion, and quality rule recommendation."""
        stg_result = self.run_p0_plus_mapping_plus_stg(tables)
        quality_output = self.quality_rule_recommendation.run(
            QualityRuleRecommendationInput(
                tables=tables,
                mapping_results=stg_result.mapping_results,
                stg_suggestions=stg_result.stg_field_suggestions,
            )
        )

        merged_skill_outputs = dict(stg_result.skill_outputs)
        merged_skill_outputs["quality_rule_output"] = self._serialize_model(quality_output)
        review_queue_summary = summarize_review_queue(
            list(quality_output.quality_rule_suggestions)
            + [
                QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
                for rule in quality_output.cross_field_quality_rules
            ]
        )
        message = stg_result.message
        if tables and stg_result.status == "success":
            message += " Quality rule recommendations were also generated."

        return WorkflowResult(
            input_table_count=stg_result.input_table_count,
            issue_count=stg_result.issue_count + len(quality_output.issues),
            task_count=stg_result.task_count,
            issues=stg_result.issues + quality_output.issues,
            tasks=stg_result.tasks,
            mapping_results=stg_result.mapping_results,
            confirmed_mapping_results=stg_result.confirmed_mapping_results,
            unmapped_fields=stg_result.unmapped_fields,
            mapping_summary=stg_result.mapping_summary,
            stg_suggestions=stg_result.stg_suggestions,
            stg_field_suggestions=stg_result.stg_field_suggestions,
            confirmed_stg_suggestions=stg_result.confirmed_stg_suggestions,
            stg_summary=stg_result.stg_summary,
            quality_rule_suggestions=quality_output.quality_rule_suggestions,
            cross_field_quality_rules=quality_output.cross_field_quality_rules,
            quality_rule_packages=quality_output.quality_rule_packages,
            quality_rule_summary=quality_output.summary,
            quality_review_queue_summary=review_queue_summary,
            skill_outputs=merged_skill_outputs,
            status=stg_result.status,
            message=message,
        )

    def run_p0_plus_mapping_plus_stg_plus_quality_with_review(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run diagnosis, mapping, STG, quality recommendation, and quality review replay."""
        reviewed_result = self.run_p0_plus_mapping_plus_stg_with_review(tables)
        effective_mapping_results = (
            reviewed_result.confirmed_mapping_results or reviewed_result.mapping_results
        )
        effective_stg_suggestions = (
            reviewed_result.confirmed_stg_suggestions
            or reviewed_result.stg_field_suggestions
        )
        quality_output = self.quality_rule_recommendation.run(
            QualityRuleRecommendationInput(
                tables=tables,
                confirmed_mapping_results=reviewed_result.confirmed_mapping_results,
                mapping_results=effective_mapping_results,
                confirmed_stg_suggestions=reviewed_result.confirmed_stg_suggestions,
                stg_suggestions=effective_stg_suggestions,
            )
        )
        reviewable_quality_rules = list(quality_output.quality_rule_suggestions) + [
            QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
            for rule in quality_output.cross_field_quality_rules
        ]
        quality_overrides = load_quality_rule_overrides()
        reviewed_quality_suggestions, applied_quality_count, quality_review_summary = (
            apply_quality_rule_overrides_to_results(
                reviewable_quality_rules,
                quality_overrides,
            )
        )
        confirmed_quality_rules = build_confirmed_quality_rules(
            reviewable_quality_rules,
            quality_overrides,
        )
        quality_review_summary = summarize_quality_rule_review_records(
            quality_overrides,
            confirmed_count=len(confirmed_quality_rules),
        )

        merged_skill_outputs = dict(reviewed_result.skill_outputs)
        merged_skill_outputs["quality_rule_output"] = self._serialize_model(quality_output)
        merged_skill_outputs["quality_rule_review_output"] = {
            "applied_quality_review_count": applied_quality_count,
            "quality_rule_review_summary": quality_review_summary,
            "confirmed_quality_rules": [
                self._serialize_model(rule) for rule in confirmed_quality_rules
            ],
        }
        field_reviewed_quality_suggestions = [
            rule for rule in reviewed_quality_suggestions if rule.rule_scope == "field"
        ]
        message = reviewed_result.message
        if tables and reviewed_result.status == "success":
            message += " Quality rule recommendations and review replay were also applied."

        return WorkflowResult(
            input_table_count=reviewed_result.input_table_count,
            issue_count=reviewed_result.issue_count + len(quality_output.issues),
            task_count=reviewed_result.task_count,
            issues=reviewed_result.issues + quality_output.issues,
            tasks=reviewed_result.tasks,
            mapping_results=reviewed_result.mapping_results,
            confirmed_mapping_results=reviewed_result.confirmed_mapping_results,
            unmapped_fields=reviewed_result.unmapped_fields,
            mapping_summary=reviewed_result.mapping_summary,
            stg_suggestions=reviewed_result.stg_suggestions,
            stg_field_suggestions=reviewed_result.stg_field_suggestions,
            confirmed_stg_suggestions=reviewed_result.confirmed_stg_suggestions,
            stg_summary=reviewed_result.stg_summary,
            quality_rule_suggestions=field_reviewed_quality_suggestions,
            cross_field_quality_rules=quality_output.cross_field_quality_rules,
            quality_rule_packages=quality_output.quality_rule_packages,
            quality_rule_summary=quality_output.summary,
            confirmed_quality_rules=confirmed_quality_rules,
            quality_rule_review_summary=quality_review_summary,
            quality_review_queue_summary=summarize_review_queue(reviewed_quality_suggestions),
            review_summary=reviewed_result.review_summary,
            skill_outputs=merged_skill_outputs,
            status=reviewed_result.status,
            message=message,
        )

    def run_p0_plus_mapping_plus_stg_plus_quality_with_package(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run quality recommendation and attach an execution package if confirmed rules exist."""
        result = self.run_p0_plus_mapping_plus_stg_plus_quality(tables)
        return self._attach_execution_ready_package(
            result,
            profile_name="diagnosis_mapping_stg_quality_package",
        )

    def run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run quality review replay and attach an execution-ready governance package."""
        result = self.run_p0_plus_mapping_plus_stg_plus_quality_with_review(tables)
        return self._attach_execution_ready_package(
            result,
            profile_name="diagnosis_mapping_stg_quality_package_with_review",
        )

    def run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_and_readiness(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run the full quality package chain and attach readiness/remediation planning."""
        result = self.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package(
            tables
        )
        return self._attach_governance_readiness(
            result,
            package_name="full_governance_work_package",
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

    def import_confirmation_workbook_and_merge(
        self,
        file_path: str,
        workbook_type: str,
    ) -> WorkflowResult:
        """Validate, import, and merge one confirmation workbook."""
        importer = ConfirmationWorkbookImporter()
        payload = importer.import_workbook(file_path, workbook_type)
        roundtrip_result = ConfirmationRoundTripService().apply_roundtrip_updates(payload)
        changed_summary = RoundTripRerunService().summarize_roundtrip_changed_objects(
            [roundtrip_result]
        )
        return WorkflowResult(
            status=roundtrip_result.status,
            message=roundtrip_result.message or "",
            workbook_import_summaries=[payload.import_summary],
            roundtrip_results=[roundtrip_result],
            roundtrip_changed_objects_summary=changed_summary,
            skill_outputs={
                "workbook_import_output": {
                    "validation_result": payload.validation_result.model_dump(),
                    "row_results": [row.model_dump() for row in payload.row_results],
                    "normalized_row_count": len(payload.normalized_rows),
                },
                "roundtrip_merge_output": roundtrip_result.model_dump(),
            },
        )

    def import_confirmation_workbook_and_rerun(
        self,
        file_path: str,
        workbook_type: str,
        rerun_changed_only: bool = True,
    ) -> WorkflowResult:
        """Import confirmation workbook and prepare changed-only rerun scope."""
        result = self.import_confirmation_workbook_and_merge(file_path, workbook_type)
        scope = RoundTripRerunService().build_rerun_scope_from_roundtrip(
            result.roundtrip_results
        )
        scope["rerun_changed_only"] = rerun_changed_only
        result.rerun_scope_summary = scope
        if result.status in {"success", "partial_success"}:
            result.message = (
                f"{result.message} Changed-object rerun scope was prepared."
            )
        result.skill_outputs["roundtrip_rerun_scope_output"] = scope
        return result

    def diagnose_confirmation_template(
        self,
        file_path: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkflowResult:
        """Diagnose a confirmation workbook template before import."""
        match_result = ConfirmationWorkbookImporter().diagnose_confirmation_template(
            file_path,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        return WorkflowResult(
            status="success" if not match_result.fallback_used else "failed",
            message=match_result.message or "",
            confirmation_template_match_result=match_result,
            skill_outputs={"confirmation_template_diagnosis_output": match_result.model_dump()},
        )

    def import_confirmation_with_template(
        self,
        file_path: str,
        template_name: str | None = None,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkflowResult:
        """Import and merge a confirmation workbook using a template profile."""
        importer = ConfirmationWorkbookImporter()
        payload = importer.import_confirmation_with_template(
            file_path,
            template_name=template_name,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        roundtrip_result = ConfirmationRoundTripService().apply_roundtrip_updates(payload)
        changed_summary = RoundTripRerunService().summarize_roundtrip_changed_objects(
            [roundtrip_result]
        )
        return WorkflowResult(
            status=roundtrip_result.status,
            message=roundtrip_result.message or "",
            workbook_import_summaries=[payload.import_summary],
            roundtrip_results=[roundtrip_result],
            roundtrip_changed_objects_summary=changed_summary,
            confirmation_template_match_result=payload.confirmation_template_match_result,
            confirmation_template_mapping_result=payload.confirmation_template_mapping_result,
            skill_outputs={
                "confirmation_template_import_output": {
                    "validation_result": payload.validation_result.model_dump(),
                    "template_match_result": (
                        payload.confirmation_template_match_result.model_dump()
                        if payload.confirmation_template_match_result
                        else None
                    ),
                    "template_mapping_result": (
                        payload.confirmation_template_mapping_result.model_dump()
                        if payload.confirmation_template_mapping_result
                        else None
                    ),
                    "row_results": [row.model_dump() for row in payload.row_results],
                    "normalized_row_count": len(payload.normalized_rows),
                },
                "roundtrip_merge_output": roundtrip_result.model_dump(),
            },
        )

    def import_confirmation_with_template_and_rerun(
        self,
        file_path: str,
        template_name: str | None = None,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
        rerun_changed_only: bool = True,
    ) -> WorkflowResult:
        """Template-aware import plus changed-object rerun scope preparation."""
        result = self.import_confirmation_with_template(
            file_path,
            template_name=template_name,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        scope = RoundTripRerunService().build_rerun_scope_from_roundtrip(
            result.roundtrip_results
        )
        scope["rerun_changed_only"] = rerun_changed_only
        result.rerun_scope_summary = scope
        if result.status in {"success", "partial_success"}:
            result.message = (
                f"{result.message} Changed-object rerun scope was prepared."
            )
        result.skill_outputs["roundtrip_rerun_scope_output"] = scope
        return result

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

    def run_quality_only_from_stg_with_review(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run mapping, STG, quality recommendation, and review replay without task packaging."""
        if not tables:
            return WorkflowResult(
                input_table_count=0,
                issue_count=0,
                task_count=0,
                mapping_results=[],
                confirmed_mapping_results=[],
                stg_suggestions=[],
                stg_field_suggestions=[],
                confirmed_stg_suggestions=[],
                quality_rule_suggestions=[],
                confirmed_quality_rules=[],
                quality_rule_review_summary={},
                skill_outputs={},
                status="empty",
                message=(
                    "No tables were provided, so quality rule recommendation with review was skipped."
                ),
            )

        naming_output = self.naming_standard_check.run(
            NamingStandardCheckInput(tables=tables)
        )
        mapping_overrides = load_mapping_overrides()
        mapping_output = self.standard_mapping_recommendation.run(
            StandardMappingInput(
                tables=tables,
                apply_overrides=True,
                override_records=mapping_overrides,
            )
        )
        stg_overrides = load_stg_overrides()
        effective_mapping_results = (
            mapping_output.confirmed_mapping_results or mapping_output.mapping_results
        )
        stg_output = self.stg_structure_suggestion.run(
            StgStructureSuggestionInput(
                tables=tables,
                mapping_results=effective_mapping_results,
                naming_field_suggestions=naming_output.field_name_suggestions,
                apply_overrides=True,
                override_records=stg_overrides,
            )
        )
        effective_stg_suggestions = (
            stg_output.confirmed_stg_suggestions or stg_output.field_suggestions_flat
        )
        quality_output = self.quality_rule_recommendation.run(
            QualityRuleRecommendationInput(
                tables=tables,
                confirmed_mapping_results=mapping_output.confirmed_mapping_results,
                mapping_results=effective_mapping_results,
                confirmed_stg_suggestions=stg_output.confirmed_stg_suggestions,
                stg_suggestions=effective_stg_suggestions,
            )
        )
        reviewable_quality_rules = list(quality_output.quality_rule_suggestions) + [
            QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
            for rule in quality_output.cross_field_quality_rules
        ]
        quality_overrides = load_quality_rule_overrides()
        reviewed_quality_suggestions, applied_quality_count, quality_review_summary = (
            apply_quality_rule_overrides_to_results(
                reviewable_quality_rules,
                quality_overrides,
            )
        )
        confirmed_quality_rules = build_confirmed_quality_rules(
            reviewable_quality_rules,
            quality_overrides,
        )
        quality_review_summary = summarize_quality_rule_review_records(
            quality_overrides,
            confirmed_count=len(confirmed_quality_rules),
        )
        review_summary = summarize_review_records(mapping_overrides, stg_overrides)
        field_reviewed_quality_suggestions = [
            rule for rule in reviewed_quality_suggestions if rule.rule_scope == "field"
        ]

        return WorkflowResult(
            input_table_count=len(tables),
            issue_count=len(mapping_output.issues) + len(stg_output.issues) + len(quality_output.issues),
            task_count=0,
            issues=mapping_output.issues + stg_output.issues + quality_output.issues,
            tasks=[],
            mapping_results=mapping_output.mapping_results,
            confirmed_mapping_results=mapping_output.confirmed_mapping_results,
            unmapped_fields=mapping_output.unmapped_fields,
            mapping_summary=mapping_output.summary,
            stg_suggestions=stg_output.stg_table_suggestions,
            stg_field_suggestions=stg_output.field_suggestions_flat,
            confirmed_stg_suggestions=stg_output.confirmed_stg_suggestions,
            stg_summary=stg_output.summary,
            quality_rule_suggestions=field_reviewed_quality_suggestions,
            cross_field_quality_rules=quality_output.cross_field_quality_rules,
            quality_rule_packages=quality_output.quality_rule_packages,
            quality_rule_summary=quality_output.summary,
            confirmed_quality_rules=confirmed_quality_rules,
            quality_rule_review_summary=quality_review_summary,
            quality_review_queue_summary=summarize_review_queue(reviewed_quality_suggestions),
            review_summary=review_summary,
            skill_outputs={
                "naming_output": self._serialize_model(naming_output),
                "standard_mapping_output": self._serialize_model(mapping_output),
                "stg_structure_output": self._serialize_model(stg_output),
                "quality_rule_output": self._serialize_model(quality_output),
                "quality_rule_review_output": {
                    "applied_quality_review_count": applied_quality_count,
                    "quality_rule_review_summary": quality_review_summary,
                    "confirmed_quality_rules": [
                        self._serialize_model(rule) for rule in confirmed_quality_rules
                    ],
                },
            },
            status="success",
            message=(
                "Rule-based mapping, STG, quality rule recommendation, and review replay "
                "executed successfully without full diagnosis packaging."
            ),
        )

    def run_quality_package_only_from_confirmed(
        self,
        tables: list[TableMeta],
    ) -> WorkflowResult:
        """Run the lightweight quality-with-review chain and attach the package layer."""
        result = self.run_quality_only_from_stg_with_review(tables)
        return self._attach_execution_ready_package(
            result,
            profile_name="quality_package_only_from_confirmed",
        )
