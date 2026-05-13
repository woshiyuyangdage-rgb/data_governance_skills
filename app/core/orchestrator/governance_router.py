"""Rule-based governance task router for named workflow profiles."""

from collections.abc import Callable

from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_confirmation_workbook_only_from_file,
    run_batch_governance_delivery_from_files,
    run_batch_governance_workflow_from_files,
    run_full_governance_backlog_package_from_file,
    run_full_governance_delivery_package_from_file,
    run_full_governance_delivery_package_with_review_from_file,
    run_full_governance_portfolio_package_from_file,
    run_full_governance_work_package_from_file,
    run_governance_backlog_build_from_file,
    run_governance_backlog_build_with_review_from_file,
    run_governance_portfolio_assessment_from_file,
    run_governance_readiness_assessment_from_file,
    run_governance_readiness_assessment_with_review_from_file,
    run_mapping_only_from_file,
    run_p0_pipeline_from_file,
    run_p0_plus_mapping_from_file,
    run_p0_plus_mapping_plus_stg_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_package_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
    run_p0_plus_mapping_plus_stg_with_review_from_file,
    run_quality_package_only_from_confirmed_from_file,
    run_quality_only_from_stg_from_file,
    run_quality_only_from_stg_with_review_from_file,
    run_stg_only_from_mapping_from_file,
)
from app.core.orchestrator.profile_exceptions import WorkflowProfileError
from app.core.orchestrator.profile_loader import (
    get_workflow_profile,
    list_enabled_profiles,
)
from app.core.reports.report_service import (
    DEFAULT_REPORT_OUTPUT_DIR,
    build_report_base_filename,
    export_all_reports,
)


class GovernanceTaskRouter:
    """Route named governance tasks to existing workflow implementations."""

    def __init__(self) -> None:
        self.enabled_profiles = {profile.name: profile for profile in list_enabled_profiles()}

    def resolve_profile_to_engine_call(
        self,
        request: GovernanceTaskRequest,
    ) -> tuple[Callable[[str], WorkflowResult], list[str]]:
        """Resolve one profile name to a file-based workflow callable."""
        profile = self.enabled_profiles.get(request.profile_name)
        if profile is None:
            profile = get_workflow_profile(request.profile_name)
        if not profile.enabled:
            raise WorkflowProfileError(
                f"Workflow profile '{request.profile_name}' is currently disabled."
            )

        if request.apply_review_replay and not profile.supports_review_replay:
            raise WorkflowProfileError(
                f"Workflow profile '{request.profile_name}' does not support review replay."
            )

        profile_routing = {
            "metadata_diagnosis_only": run_p0_pipeline_from_file,
            "diagnosis_plus_mapping": run_p0_plus_mapping_from_file,
            "diagnosis_mapping_stg": run_p0_plus_mapping_plus_stg_from_file,
            "diagnosis_mapping_stg_with_review": run_p0_plus_mapping_plus_stg_with_review_from_file,
            "diagnosis_mapping_stg_quality": run_p0_plus_mapping_plus_stg_plus_quality_from_file,
            "diagnosis_mapping_stg_quality_with_review": run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
            "diagnosis_mapping_stg_quality_package": run_p0_plus_mapping_plus_stg_plus_quality_with_package_from_file,
            "diagnosis_mapping_stg_quality_package_with_review": run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
            "governance_readiness_assessment": run_governance_readiness_assessment_from_file,
            "governance_readiness_assessment_with_review": run_governance_readiness_assessment_with_review_from_file,
            "full_governance_work_package": run_full_governance_work_package_from_file,
            "governance_backlog_build": run_governance_backlog_build_from_file,
            "governance_backlog_build_with_review": run_governance_backlog_build_with_review_from_file,
            "full_governance_backlog_package": run_full_governance_backlog_package_from_file,
            "governance_portfolio_assessment": run_governance_portfolio_assessment_from_file,
            "full_governance_portfolio_package": run_full_governance_portfolio_package_from_file,
            "governance_delivery_package": run_full_governance_delivery_package_from_file,
            "governance_delivery_package_with_review": run_full_governance_delivery_package_with_review_from_file,
            "confirmation_workbook_only": run_confirmation_workbook_only_from_file,
            "quality_package_only_from_confirmed": run_quality_package_only_from_confirmed_from_file,
            "mapping_only": run_mapping_only_from_file,
            "stg_only_from_mapping": run_stg_only_from_mapping_from_file,
            "quality_only_from_stg": run_quality_only_from_stg_from_file,
            "quality_only_from_stg_with_review": run_quality_only_from_stg_with_review_from_file,
        }
        handler = profile_routing.get(profile.name)
        if handler is None:
            raise WorkflowProfileError(
                f"No workflow handler is registered for profile '{profile.name}'."
            )

        return handler, list(profile.stages)

    def maybe_export_reports(
        self,
        request: GovernanceTaskRequest,
        result: WorkflowResult,
    ) -> dict[str, str] | None:
        """Optionally export workflow reports for successful runs."""
        if not request.export_reports or result.status != "success":
            return None

        output_dir = request.output_dir or str(DEFAULT_REPORT_OUTPUT_DIR)
        base_filename = build_report_base_filename(
            profile_name=request.profile_name,
            base_filename=request.base_filename,
        )
        return export_all_reports(result, output_dir, base_filename)

    @staticmethod
    def build_task_response(
        request: GovernanceTaskRequest,
        result: WorkflowResult,
        stages_executed: list[str],
        exported_files: dict[str, str] | None = None,
    ) -> GovernanceTaskResponse:
        """Build a normalized task response."""
        return GovernanceTaskResponse(
            profile_name=request.profile_name,
            status=result.status,
            message=result.message,
            stages_executed=stages_executed,
            result=result,
            exported_files=exported_files,
        )

    def run_task(self, request: GovernanceTaskRequest) -> GovernanceTaskResponse:
        """Run one governance task using a named workflow profile."""
        if request.profile_name == "run_project_template":
            if not request.file_path or not request.template_name:
                empty_result = WorkflowResult(
                    status="failed",
                    message="Both file_path and template_name are required for project template execution.",
                )
                return self.build_task_response(request, empty_result, [])
            engine = __import__(
                "app.core.orchestrator.workflow_engine",
                fromlist=["WorkflowEngine"],
            ).WorkflowEngine()
            result = engine.run_project_template(
                request.template_name,
                request.file_path,
                domain_pack_name=request.domain_pack_name,
                output_dir=request.output_dir,
            )
            stages = []
            if result.project_template_result is not None and result.project_template_result.workflow_profile:
                stages = list(get_workflow_profile(result.project_template_result.workflow_profile).stages)
            exported_files = self.maybe_export_reports(request, result)
            return self.build_task_response(request, result, stages, exported_files)

        batch_profiles = {
            "batch_governance_run",
            "batch_incremental_rerun",
            "batch_delivery_package",
        }
        if request.profile_name in batch_profiles:
            file_paths = list(request.file_paths or [])
            if request.file_path:
                file_paths.append(request.file_path)
            if not file_paths:
                empty_result = WorkflowResult(
                    status="failed",
                    message="At least one file_path or file_paths entry is required for batch execution.",
                )
                return self.build_task_response(request, empty_result, [])
            profile = get_workflow_profile(request.profile_name)
            changed_only = request.profile_name == "batch_incremental_rerun"
            if request.profile_name == "batch_delivery_package":
                result = run_batch_governance_delivery_from_files(
                    file_paths,
                    changed_only=False,
                    batch_name=request.base_filename,
                )
            else:
                result = run_batch_governance_workflow_from_files(
                    file_paths,
                    changed_only=changed_only,
                    batch_name=request.base_filename,
                )
            return self.build_task_response(request, result, list(profile.stages))

        roundtrip_profiles = {
            "import_confirmation_workbook",
            "import_and_rerun_changed_objects",
        }
        if request.profile_name in roundtrip_profiles:
            if not request.file_path:
                empty_result = WorkflowResult(
                    status="failed",
                    message="A local file_path is required for workbook import.",
                )
                return self.build_task_response(request, empty_result, [])
            workbook_type = request.workbook_type or "mapping_confirmation"
            profile = get_workflow_profile(request.profile_name)
            engine = __import__(
                "app.core.orchestrator.workflow_engine",
                fromlist=["WorkflowEngine"],
            ).WorkflowEngine()
            if request.profile_name == "import_and_rerun_changed_objects":
                result = engine.import_confirmation_workbook_and_rerun(
                    request.file_path,
                    workbook_type,
                    rerun_changed_only=True,
                )
            else:
                result = engine.import_confirmation_workbook_and_merge(
                    request.file_path,
                    workbook_type,
                )
            return self.build_task_response(request, result, list(profile.stages))

        confirmation_template_profiles = {
            "diagnose_confirmation_template",
            "import_confirmation_with_template",
            "import_confirmation_template_and_rerun",
        }
        if request.profile_name in confirmation_template_profiles:
            if not request.file_path:
                empty_result = WorkflowResult(
                    status="failed",
                    message="A local file_path is required for confirmation template execution.",
                )
                return self.build_task_response(request, empty_result, [])
            profile = get_workflow_profile(request.profile_name)
            engine = __import__(
                "app.core.orchestrator.workflow_engine",
                fromlist=["WorkflowEngine"],
            ).WorkflowEngine()
            if request.profile_name == "diagnose_confirmation_template":
                result = engine.diagnose_confirmation_template(
                    request.file_path,
                    workbook_type=request.workbook_type,
                    sheet_name=request.sheet_name,
                )
            elif request.profile_name == "import_confirmation_template_and_rerun":
                result = engine.import_confirmation_with_template_and_rerun(
                    request.file_path,
                    template_name=request.confirmation_template_name,
                    workbook_type=request.workbook_type,
                    sheet_name=request.sheet_name,
                    rerun_changed_only=True,
                )
            else:
                result = engine.import_confirmation_with_template(
                    request.file_path,
                    template_name=request.confirmation_template_name,
                    workbook_type=request.workbook_type,
                    sheet_name=request.sheet_name,
                )
            return self.build_task_response(request, result, list(profile.stages))

        if not request.file_path:
            empty_result = WorkflowResult(
                status="failed",
                message="A local file_path is required for governance task execution.",
            )
            return self.build_task_response(request, empty_result, [])

        try:
            handler, stages_executed = self.resolve_profile_to_engine_call(request)
            if request.intake_profile_name or request.auto_match_template:
                engine = __import__(
                    "app.core.orchestrator.workflow_engine",
                    fromlist=["WorkflowEngine"],
                ).WorkflowEngine()
                result = engine.run_governance_with_intake_profile(
                    request.file_path,
                    profile_name=request.profile_name,
                    intake_profile_name=request.intake_profile_name,
                    sheet_name=request.sheet_name,
                )
            else:
                result = handler(request.file_path)
            if request.domain_pack_name:
                result.skill_outputs = {
                    **dict(result.skill_outputs),
                    "domain_pack_hint": {
                        "domain_pack_name": request.domain_pack_name,
                        "message": "Domain pack hint attached to workflow result.",
                    },
                }
            exported_files = self.maybe_export_reports(request, result)
            return self.build_task_response(
                request=request,
                result=result,
                stages_executed=stages_executed,
                exported_files=exported_files,
            )
        except WorkflowProfileError as exc:
            failed_result = WorkflowResult(status="failed", message=str(exc))
            return self.build_task_response(request, failed_result, [])
        except Exception as exc:
            failed_result = WorkflowResult(
                status="failed",
                message=f"Unexpected error while running governance task '{request.profile_name}': {exc}",
            )
            return self.build_task_response(request, failed_result, [])


# TODO: extend the router with natural-language task interpretation and agent-driven stage planning in a future version.
