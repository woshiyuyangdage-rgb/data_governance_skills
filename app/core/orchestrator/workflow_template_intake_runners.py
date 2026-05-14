"""Project template and intake-aware workflow runners."""

from app.core.models.workflow_result import WorkflowResult


class WorkflowTemplateIntakeRunnerMixin:
    """Run project template and metadata intake workflows."""

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
