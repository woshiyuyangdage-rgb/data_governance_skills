"""Mapping and STG workflow runner helpers."""

from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.review.override_store import load_mapping_overrides, load_stg_overrides
from app.core.review.review_service import summarize_review_records
from app.core.skills.data_standard_mapping_skill import StandardMappingInput
from app.core.skills.metadata_diagnosis_skill import NamingStandardCheckInput
from app.core.skills.metadata_diagnosis_skill import MetadataSemanticEnrichmentInput
from app.core.skills.stg_standardization_skill import StgStructureSuggestionInput


class WorkflowMappingStgRunnerMixin:
    """Run mapping and STG workflow stages."""

    def run_standard_mapping(self, tables: list[TableMeta]) -> WorkflowResult:
        """Run only the P1 standard mapping recommendation skill."""
        mapping_output = self.standard_mapping_recommendation.run(
            StandardMappingInput(tables=tables, apply_overrides=False)
        )
        semantic_enrichment_output = self.metadata_semantic_enrichment.run(
            MetadataSemanticEnrichmentInput(tables=tables)
        )
        return WorkflowResult(
            input_table_count=len(tables),
            issue_count=len(mapping_output.issues),
            task_count=0,
            issues=mapping_output.issues,
            tasks=[],
            field_description_suggestions=(
                semantic_enrichment_output.field_description_suggestions
            ),
            table_semantic_summaries=(
                semantic_enrichment_output.table_semantic_summaries
            ),
            semantic_enrichment_summary=semantic_enrichment_output.summary,
            mapping_results=mapping_output.mapping_results,
            confirmed_mapping_results=[],
            unmapped_fields=mapping_output.unmapped_fields,
            mapping_summary=mapping_output.summary,
            skill_outputs={
                "semantic_enrichment_output": self._serialize_model(
                    semantic_enrichment_output
                ),
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
        semantic_enrichment_output = self.metadata_semantic_enrichment.run(
            MetadataSemanticEnrichmentInput(tables=tables)
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
            field_description_suggestions=(
                semantic_enrichment_output.field_description_suggestions
            ),
            table_semantic_summaries=(
                semantic_enrichment_output.table_semantic_summaries
            ),
            semantic_enrichment_summary=semantic_enrichment_output.summary,
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
                "semantic_enrichment_output": self._serialize_model(
                    semantic_enrichment_output
                ),
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
            field_description_suggestions=p0_result.field_description_suggestions,
            table_semantic_summaries=p0_result.table_semantic_summaries,
            semantic_enrichment_summary=p0_result.semantic_enrichment_summary,
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
            field_description_suggestions=p0_result.field_description_suggestions,
            table_semantic_summaries=p0_result.table_semantic_summaries,
            semantic_enrichment_summary=p0_result.semantic_enrichment_summary,
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
            field_description_suggestions=(
                mapping_result.field_description_suggestions
            ),
            table_semantic_summaries=mapping_result.table_semantic_summaries,
            semantic_enrichment_summary=(
                mapping_result.semantic_enrichment_summary
            ),
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
            field_description_suggestions=(
                mapping_result.field_description_suggestions
            ),
            table_semantic_summaries=mapping_result.table_semantic_summaries,
            semantic_enrichment_summary=(
                mapping_result.semantic_enrichment_summary
            ),
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
