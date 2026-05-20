"""Quality rule workflow runner helpers."""

from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.review.override_store import load_mapping_overrides, load_stg_overrides
from app.core.review.quality_batch_review_service import summarize_review_queue
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    summarize_quality_rule_review_records,
)
from app.core.review.review_service import summarize_review_records
from app.core.skills.data_quality_rule_skill import (
    QualityRuleRecommendationInput,
    QualityRuleRecommendationSkill,
)
from app.core.skills.data_standard_mapping_skill import StandardMappingInput
from app.core.skills.metadata_diagnosis_skill import NamingStandardCheckInput
from app.core.skills.stg_standardization_skill import StgStructureSuggestionInput


class WorkflowQualityRunnerMixin:
    """Run quality rule recommendation and review workflows."""

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
        merged_skill_outputs["quality_rule_output"] = self._serialize_model(
            quality_output
        )
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
        merged_skill_outputs["quality_rule_output"] = self._serialize_model(
            quality_output
        )
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
        merged_skill_outputs["quality_rule_output"] = self._serialize_model(
            quality_output
        )
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
            quality_review_queue_summary=summarize_review_queue(
                reviewed_quality_suggestions
            ),
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
            issue_count=(
                len(mapping_output.issues)
                + len(stg_output.issues)
                + len(quality_output.issues)
            ),
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
            quality_review_queue_summary=summarize_review_queue(
                reviewed_quality_suggestions
            ),
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
