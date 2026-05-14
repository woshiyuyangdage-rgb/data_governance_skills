"""Routes for governance job execution."""

from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.api.job_catalog import build_job_catalog
from app.api.job_requests import (
    AgentShellPlanRequest,
    AgentShellRunRequest,
    BatchGovernanceRequest,
    BatchSnapshotCompareRequest,
    ConfigAssetSaveRequest,
    ConfirmationTemplateRequest,
    ConfirmationWorkbookImportRequest,
    ConfirmedQualityRuleExportRequest,
    DomainPackMatchRequest,
    ExecutionPackageBuildRequest,
    ExecutionPackageExportRequest,
    FileRunRequest,
    GovernanceBacklogBuildRequest,
    GovernanceBacklogStatusUpdateRequest,
    GovernanceDeliveryPackageRequest,
    GovernancePortfolioAssessmentRequest,
    GovernanceReadinessAssessmentRequest,
    GovernanceWorkPackageBuildRequest,
    IntentTextRequest,
    MappingReviewSaveRequest,
    MetadataIntakeRequest,
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
    ProgressSnapshotRequest,
    ProjectTemplateRunRequest,
    QualityRuleReviewRequest,
    StgReviewSaveRequest,
)
from app.api.tool_response import (
    call_tool_and_expand,
    call_tool_and_wrap,
    call_tool_or_400,
)
from app.core.agent.agent_shell_service import AgentShellService
from app.core.adapters.invocation_adapter import InvocationAdapter
from app.core.adapters.manifest_service import (
    get_capability_manifest,
    get_mcp_style_manifest,
    get_native_tool_schemas,
    get_openai_tool_schemas,
)
from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.audit.trace_store import get_trace, list_recent_traces
from app.core.agent.session_store import get_session
from app.core.control_plane.control_plane_service import ControlPlaneService
from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.models.agent_session import AgentSession
from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.adapter_invocation_result import AdapterInvocationResult
from app.core.models.capability_manifest import CapabilityManifest
from app.core.models.config_edit_result import ConfigEditResult
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.execution_trace import ExecutionTrace
from app.core.models.exported_tool_schema import ExportedToolSchema
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.review_summary import ReviewSummary
from app.core.models.rule_export_result import RuleExportResult
from app.core.models.tool_call_request import ToolCallRequest
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.tool_definition import ToolDefinition
from app.core.models.validation_result import ValidationResult
from app.core.models.workflow_profile import WorkflowProfile
from app.core.models.workflow_result import WorkflowResult
from app.core.intent.intent_task_service import (
    interpret_and_build_request,
    interpret_and_run_task,
)
from app.core.intake.intake_adapter_service import IntakeAdapterService
from app.core.models.intake_match_result import IntakeMatchResult
from app.core.models.intake_normalization_result import IntakeNormalizationResult
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.orchestrator.pipeline_service import (
    run_mapping_only_from_file,
    run_p0_pipeline_from_file,
    run_p0_plus_mapping_from_file,
    run_p0_plus_mapping_plus_stg_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
    run_p0_plus_mapping_plus_stg_with_review_from_file,
    run_quality_only_from_stg_from_file,
    run_quality_only_from_stg_with_review_from_file,
    run_stg_only_from_mapping_from_file,
)
from app.core.orchestrator.task_service import run_governance_task
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.review.quality_override_store import (
    load_quality_rule_overrides,
    save_quality_rule_review_records,
)
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.review.override_store import (
    load_mapping_overrides,
    load_stg_overrides,
    save_mapping_review_records,
    save_stg_review_records,
)
from app.core.review.review_service import summarize_review_records
from app.core.skills.quality_rule_recommendation import QualityRuleRecommendationSkill
from app.core.tools.tool_service import call_tool, list_tools
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.governance.batch_snapshot_store import list_batch_snapshots
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.templates.project_template_service import ProjectTemplateService

router = APIRouter(prefix="/jobs", tags=["jobs"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
control_plane_service = ControlPlaneService()
invocation_adapter = InvocationAdapter()


@router.get("/domain-governance-packs")
def get_domain_governance_packs() -> dict[str, object]:
    """List enabled domain governance packs."""
    packs = [pack.model_dump() for pack in list_enabled_domain_packs()]
    return {"packs": packs, "count": len(packs)}


@router.get("/project-templates")
def get_project_templates() -> dict[str, object]:
    """List enabled project template profiles."""
    templates = [template.model_dump() for template in list_enabled_project_templates()]
    return {"templates": templates, "count": len(templates)}


@router.post("/match-domain-governance-pack")
def match_domain_governance_pack(request: DomainPackMatchRequest) -> dict[str, object]:
    """Match a domain governance pack from provided text."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text is required.")
    match = DomainPackMatcher().match_domain_pack_from_text(request.text)
    return match.model_dump()


@router.post("/run-project-template", response_model=WorkflowResult)
def run_project_template(request: ProjectTemplateRunRequest) -> WorkflowResult:
    """Run a project template with optional domain pack override."""
    try:
        return ProjectTemplateService().run_project_template(
            template_name=request.template_name,
            file_path=request.file_path,
            domain_pack_name=request.domain_pack_name,
            output_dir=request.output_dir,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to run project template: {exc}",
        ) from exc


@router.post("/diagnose-metadata-intake-template", response_model=IntakeMatchResult)
def diagnose_metadata_intake_template(request: MetadataIntakeRequest) -> IntakeMatchResult:
    """Diagnose which intake template best matches a metadata file."""
    try:
        return IntakeAdapterService().diagnose_intake_template(
            request.file_path,
            sheet_name=request.sheet_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to diagnose metadata intake template: {exc}",
        ) from exc


@router.post("/normalize-metadata-input", response_model=IntakeNormalizationResult)
def normalize_metadata_input(request: MetadataIntakeRequest) -> IntakeNormalizationResult:
    """Normalize a metadata intake file into standard records."""
    try:
        return IntakeAdapterService().normalize_metadata_input(
            request.file_path,
            profile_name=request.intake_profile_name,
            sheet_name=request.sheet_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to normalize metadata input: {exc}",
        ) from exc


@router.post("/run-governance-with-intake-profile", response_model=WorkflowResult)
def run_governance_with_intake_profile(request: MetadataIntakeRequest) -> WorkflowResult:
    """Normalize metadata through intake adapter and run governance workflow."""
    try:
        return WorkflowEngine().run_governance_with_intake_profile(
            request.file_path,
            profile_name=request.profile_name,
            intake_profile_name=request.intake_profile_name,
            sheet_name=request.sheet_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to run governance with intake profile: {exc}",
        ) from exc


@router.post("/diagnose-confirmation-template", response_model=ConfirmationTemplateMatchResult)
def diagnose_confirmation_template(request: ConfirmationTemplateRequest) -> ConfirmationTemplateMatchResult:
    """Diagnose a confirmation workbook template before import."""
    try:
        return ConfirmationWorkbookImporter().diagnose_confirmation_template(
            request.file_path,
            workbook_type=request.workbook_type,
            sheet_name=request.sheet_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to diagnose confirmation template: {exc}",
        ) from exc


@router.post("/import-confirmation-with-template", response_model=WorkflowResult)
def import_confirmation_with_template(request: ConfirmationTemplateRequest) -> WorkflowResult:
    """Import and merge a confirmation workbook using template-specific mapping."""
    try:
        return WorkflowEngine().import_confirmation_with_template(
            request.file_path,
            template_name=request.confirmation_template_name,
            workbook_type=request.workbook_type,
            sheet_name=request.sheet_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import confirmation workbook with template: {exc}",
        ) from exc


@router.post("/import-confirmation-template-and-rerun", response_model=WorkflowResult)
def import_confirmation_template_and_rerun(request: ConfirmationTemplateRequest) -> WorkflowResult:
    """Template-aware confirmation import plus changed-object rerun scope."""
    try:
        return WorkflowEngine().import_confirmation_with_template_and_rerun(
            request.file_path,
            template_name=request.confirmation_template_name,
            workbook_type=request.workbook_type,
            sheet_name=request.sheet_name,
            rerun_changed_only=request.rerun_changed_only,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import confirmation template and rerun: {exc}",
        ) from exc


@router.get("/")
def list_jobs() -> dict[str, object]:
    """Return a small catalog of available demo jobs."""
    return build_job_catalog()


@router.post("/run-p0-demo", response_model=WorkflowResult)
def run_p0_demo() -> WorkflowResult:
    """Run the rule-based P0 pipeline on built-in demo tables."""
    engine = WorkflowEngine()
    return engine.run_p0_pipeline(engine.build_demo_tables())


@router.post("/run-p0-from-file", response_model=WorkflowResult)
def run_p0_from_file(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based P0 pipeline from a local metadata file path."""
    return run_p0_pipeline_from_file(payload.file_path)


@router.post("/run-p0-plus-mapping", response_model=WorkflowResult)
def run_p0_plus_mapping(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based P0 pipeline and standard mapping from a local file path."""
    return run_p0_plus_mapping_from_file(payload.file_path)


@router.post("/run-p0-plus-mapping-plus-stg", response_model=WorkflowResult)
def run_p0_plus_mapping_plus_stg(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based P0 pipeline, standard mapping, and STG suggestion from a local file path."""
    return run_p0_plus_mapping_plus_stg_from_file(payload.file_path)


@router.post("/run-p0-plus-mapping-plus-stg-with-review", response_model=WorkflowResult)
def run_p0_plus_mapping_plus_stg_with_review(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based workflow with saved review overrides applied."""
    return run_p0_plus_mapping_plus_stg_with_review_from_file(payload.file_path)


@router.post("/run-p0-plus-mapping-plus-stg-plus-quality", response_model=WorkflowResult)
def run_p0_plus_mapping_plus_stg_plus_quality(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based diagnosis, mapping, STG, and quality workflow from a local file path."""
    return run_p0_plus_mapping_plus_stg_plus_quality_from_file(payload.file_path)


@router.post(
    "/run-p0-plus-mapping-plus-stg-plus-quality-with-review",
    response_model=WorkflowResult,
)
def run_p0_plus_mapping_plus_stg_plus_quality_with_review(
    payload: FileRunRequest,
) -> WorkflowResult:
    """Run the rule-based diagnosis, mapping, STG, and quality workflow with review replay."""
    return run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
        payload.file_path
    )


@router.post("/run-mapping-only", response_model=WorkflowResult)
def run_mapping_only(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based mapping-only workflow from a local file path."""
    return run_mapping_only_from_file(payload.file_path)


@router.post("/run-stg-only-from-mapping", response_model=WorkflowResult)
def run_stg_only_from_mapping(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based mapping plus STG workflow without full diagnosis packaging."""
    return run_stg_only_from_mapping_from_file(payload.file_path)


@router.post("/run-quality-only-from-stg", response_model=WorkflowResult)
def run_quality_only_from_stg(payload: FileRunRequest) -> WorkflowResult:
    """Run the rule-based mapping, STG, and quality workflow without full diagnosis packaging."""
    return run_quality_only_from_stg_from_file(payload.file_path)


@router.post("/run-quality-only-from-stg-with-review", response_model=WorkflowResult)
def run_quality_only_from_stg_with_review(payload: FileRunRequest) -> WorkflowResult:
    """Run mapping, STG, quality, and review replay without full diagnosis packaging."""
    return run_quality_only_from_stg_with_review_from_file(payload.file_path)


@router.post("/run-governance-task", response_model=GovernanceTaskResponse)
def run_governance_task_route(payload: GovernanceTaskRequest) -> GovernanceTaskResponse:
    """Run a unified governance task request through the workflow profile router."""
    return run_governance_task(payload)


@router.get("/list-workflow-profiles", response_model=list[WorkflowProfile])
def list_workflow_profiles() -> list[WorkflowProfile]:
    """Return enabled workflow profiles for UI and future agent callers."""
    return list_enabled_profiles()


@router.post("/interpret-governance-task", response_model=IntentExecutionResult)
def interpret_governance_task(payload: IntentTextRequest) -> IntentExecutionResult:
    """Interpret task text into a governance task request without executing it."""
    return interpret_and_build_request(payload.text, payload.file_path)


@router.post("/run-interpreted-governance-task", response_model=IntentExecutionResult)
def run_interpreted_governance_task(payload: IntentTextRequest) -> IntentExecutionResult:
    """Interpret task text and execute it through the governance router."""
    return interpret_and_run_task(payload.text, payload.file_path)


@router.post("/agent-shell/plan", response_model=AgentShellResult)
def agent_shell_plan(payload: AgentShellPlanRequest) -> AgentShellResult:
    """Interpret task text and return a previewable execution plan."""
    service = AgentShellService()
    return service.interpret_to_plan(
        text=payload.text,
        file_path=payload.file_path,
        session_id=payload.session_id,
    )


@router.post("/agent-shell/resolve-context", response_model=AgentShellResult)
def agent_shell_resolve_context(payload: AgentShellPlanRequest) -> AgentShellResult:
    """Interpret task text, resolve local context, and return a previewable plan."""
    service = AgentShellService()
    return service.interpret_to_plan(
        text=payload.text,
        file_path=payload.file_path,
        session_id=payload.session_id,
    )


@router.post("/agent-shell/run", response_model=AgentShellResult)
def agent_shell_run(payload: AgentShellRunRequest) -> AgentShellResult:
    """Interpret task text, build a plan, and run it when policy allows."""
    service = AgentShellService()
    return service.confirm_and_run(
        text=payload.text,
        file_path=payload.file_path,
        session_id=payload.session_id,
        force_run=payload.force_run,
    )


@router.get("/agent-shell/session/{session_id}", response_model=AgentSession | None)
def agent_shell_session(session_id: str) -> AgentSession | None:
    """Return a local agent shell session if it exists."""
    return get_session(session_id)


@router.get("/list-tools", response_model=list[ToolDefinition])
def list_tools_route() -> list[ToolDefinition]:
    """Return enabled local governance tool definitions."""
    return list_tools()


@router.post("/call-tool", response_model=ToolCallResponse)
def call_tool_route(payload: ToolCallRequest) -> ToolCallResponse:
    """Call one governance tool through the local tool contract layer."""
    return call_tool(payload)


@router.get("/capability-manifest", response_model=CapabilityManifest)
def capability_manifest_route() -> CapabilityManifest:
    """Return the adapter-layer capability manifest."""
    return get_capability_manifest()


@router.get("/tool-schemas/native", response_model=list[ExportedToolSchema])
def native_tool_schemas_route() -> list[ExportedToolSchema]:
    """Return native adapter-layer tool schemas."""
    return get_native_tool_schemas()


@router.get("/tool-schemas/openai", response_model=list[dict[str, object]])
def openai_tool_schemas_route() -> list[dict[str, object]]:
    """Return simplified OpenAI-style function schemas."""
    return get_openai_tool_schemas()


@router.get("/tool-schemas/mcp", response_model=dict[str, object])
def mcp_tool_manifest_route() -> dict[str, object]:
    """Return a lightweight local MCP-style manifest."""
    return get_mcp_style_manifest()


@router.post("/invoke-native-tool", response_model=AdapterInvocationResult)
def invoke_native_tool_route(payload: NativeToolInvokeRequest) -> AdapterInvocationResult:
    """Invoke one local governance tool through the native adapter shape."""
    return invocation_adapter.invoke_native_tool(
        tool_name=payload.tool_name,
        arguments=payload.arguments,
    )


@router.post("/invoke-openai-tool", response_model=AdapterInvocationResult)
def invoke_openai_tool_route(payload: OpenAIToolInvokeRequest) -> AdapterInvocationResult:
    """Invoke one local governance tool through the simplified OpenAI-style shape."""
    return invocation_adapter.invoke_openai_style(
        function_name=payload.function_name,
        arguments_json=payload.arguments_json,
    )


@router.get("/trace/{trace_id}", response_model=ExecutionTrace | None)
def get_trace_route(trace_id: str) -> ExecutionTrace | None:
    """Return one saved execution trace if it exists."""
    return get_trace(trace_id)


@router.get("/traces/recent", response_model=list[ExecutionTrace])
def list_recent_traces_route(limit: int = 20) -> list[ExecutionTrace]:
    """Return recent execution traces from local audit storage."""
    return list_recent_traces(limit=limit)


@router.get("/config-assets", response_model=list[dict[str, object]])
def list_config_assets_route() -> list[dict[str, object]]:
    """Return managed control-plane assets with their current status."""
    return control_plane_service.list_assets_with_status()


@router.get("/config-assets/{asset_name}", response_model=dict[str, object])
def get_config_asset_route(asset_name: str) -> dict[str, object]:
    """Return one managed config asset with current content and status."""
    try:
        return control_plane_service.get_asset_content(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/validate",
    response_model=ValidationResult,
)
def validate_config_asset_route(asset_name: str) -> ValidationResult:
    """Validate one managed config asset."""
    try:
        return control_plane_service.validate_asset(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/save",
    response_model=ConfigEditResult,
)
def save_config_asset_route(
    asset_name: str,
    payload: ConfigAssetSaveRequest,
) -> ConfigEditResult:
    """Save one managed config asset after validation."""
    try:
        return control_plane_service.save_asset(asset_name, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/config-assets/{asset_name}/publish",
    response_model=ConfigEditResult,
)
def publish_config_asset_route(asset_name: str) -> ConfigEditResult:
    """Publish one managed config asset after validation."""
    try:
        return control_plane_service.publish_asset(asset_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/save-mapping-review")
def save_mapping_review(payload: MappingReviewSaveRequest) -> dict[str, object]:
    """Save mapping review records to local override storage."""
    result = save_mapping_review_records(payload.records)
    return {
        "message": "Mapping review records were saved successfully.",
        "saved_count": result["saved_count"],
        "path": result["path"],
        "history_path": result["history_path"],
    }


@router.post("/save-stg-review")
def save_stg_review(payload: StgReviewSaveRequest) -> dict[str, object]:
    """Save STG review records to local override storage."""
    result = save_stg_review_records(payload.records)
    return {
        "message": "STG review records were saved successfully.",
        "saved_count": result["saved_count"],
        "path": result["path"],
        "history_path": result["history_path"],
    }


@router.get("/list-review-summary", response_model=ReviewSummary)
def list_review_summary() -> ReviewSummary:
    """Return aggregated counts from locally stored review overrides."""
    return summarize_review_records(load_mapping_overrides(), load_stg_overrides())


@router.post("/review-quality-rules")
def review_quality_rules_route(payload: QualityRuleReviewRequest) -> dict[str, object]:
    """Review quality rule suggestions and build confirmed quality rules."""
    try:
        suggestions = list(payload.quality_rule_suggestions)
        cross_field_rules = list(payload.cross_field_quality_rules)
        if not suggestions and payload.workflow_result is not None:
            suggestions = list(payload.workflow_result.quality_rule_suggestions)
        if not cross_field_rules and payload.workflow_result is not None:
            cross_field_rules = list(payload.workflow_result.cross_field_quality_rules)
        suggestions = suggestions + [
            QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
            for rule in cross_field_rules
        ]
        if not suggestions:
            raise ValueError(
                "quality_rule_suggestions, cross_field_quality_rules, or workflow_result suggestions are required."
            )

        records = list(payload.records)
        if not records:
            records = build_quality_rule_review_records_from_results(
                suggestions,
                payload.review_inputs,
                source=payload.source,
            )

        reviewed_suggestions, applied_count, _ = apply_quality_rule_overrides_to_results(
            suggestions,
            records,
        )
        confirmed_rules = build_confirmed_quality_rules(suggestions, records)
        summary = summarize_quality_rule_review_records(
            records,
            confirmed_count=len(confirmed_rules),
        )
        saved_payload = (
            save_quality_rule_review_records(records) if payload.save_overrides else None
        )
        return {
            "message": "Quality rules were reviewed successfully.",
            "review_records": [record.model_dump() for record in records],
            "reviewed_quality_rule_suggestions": [
                suggestion.model_dump() for suggestion in reviewed_suggestions
            ],
            "confirmed_quality_rules": [rule.model_dump() for rule in confirmed_rules],
            "quality_rule_review_summary": summary,
            "applied_quality_review_count": applied_count,
            "saved": saved_payload,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export-confirmed-quality-rules")
def export_confirmed_quality_rules_route(
    payload: ConfirmedQualityRuleExportRequest,
) -> dict[str, object]:
    """Export confirmed quality rules as JSON or dbt YAML."""
    try:
        confirmed_rules = list(payload.confirmed_quality_rules)
        workflow_result = payload.workflow_result
        if not confirmed_rules and workflow_result is not None:
            confirmed_rules = list(workflow_result.confirmed_quality_rules)

        if not confirmed_rules and payload.file_path:
            workflow_result = (
                run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
                    payload.file_path
                )
                if payload.apply_review_replay
                else run_p0_plus_mapping_plus_stg_plus_quality_from_file(payload.file_path)
            )
            confirmed_rules = list(workflow_result.confirmed_quality_rules)
            if not confirmed_rules and payload.apply_review_replay:
                review_queue = list(workflow_result.quality_rule_suggestions) + [
                    QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
                    for rule in workflow_result.cross_field_quality_rules
                ]
                confirmed_rules = build_confirmed_quality_rules(
                    review_queue,
                    load_quality_rule_overrides(),
                )

        output_dir = Path(payload.output_dir or PROJECT_ROOT / "outputs" / "rule_exports")
        base_filename = payload.base_filename or (
            f"confirmed_quality_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        normalized_format = {
            "json": "custom_json",
            "custom_json": "custom_json",
            "dbt": "dbt_yaml",
            "dbt_yaml": "dbt_yaml",
            "yaml": "dbt_yaml",
        }.get(payload.export_format.lower(), payload.export_format.lower())

        adapter = RuleExportAdapter()
        export_results: list[RuleExportResult] = []
        if normalized_format in {"custom_json", "both"}:
            export_results.append(
                adapter.export_custom_json_rules(
                    confirmed_rules,
                    str(output_dir / f"{base_filename}.json"),
                )
            )
        if normalized_format in {"dbt_yaml", "both"}:
            export_results.append(
                adapter.export_dbt_tests_yaml(
                    confirmed_rules,
                    str(output_dir / f"{base_filename}_dbt.yml"),
                )
            )
        if not export_results:
            raise ValueError(
                "export_format must be one of json, custom_json, dbt, dbt_yaml, yaml, or both."
            )

        return {
            "message": "Confirmed quality rules were exported successfully.",
            "confirmed_rule_count": len(confirmed_rules),
            "rule_export_results": [result.model_dump() for result in export_results],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolve_execution_ready_package_from_payload(
    payload: ExecutionPackageBuildRequest | ExecutionPackageExportRequest,
) -> tuple[ExecutionReadyPackage, list[ConfirmedQualityRule]]:
    """Resolve or build an execution-ready package for API routes."""
    if payload.execution_ready_package is not None:
        return payload.execution_ready_package, list(payload.confirmed_quality_rules)

    confirmed_rules = list(payload.confirmed_quality_rules)
    workflow_result = payload.workflow_result
    if workflow_result is not None and workflow_result.execution_ready_package is not None:
        return workflow_result.execution_ready_package, list(workflow_result.confirmed_quality_rules)
    if not confirmed_rules and workflow_result is not None:
        confirmed_rules = list(workflow_result.confirmed_quality_rules)

    if not confirmed_rules and payload.file_path:
        workflow_result = (
            run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
                payload.file_path
            )
            if payload.apply_review_replay
            else run_p0_plus_mapping_plus_stg_plus_quality_from_file(payload.file_path)
        )
        if workflow_result.execution_ready_package is not None:
            return workflow_result.execution_ready_package, list(
                workflow_result.confirmed_quality_rules
            )
        confirmed_rules = list(workflow_result.confirmed_quality_rules)

    if not confirmed_rules and payload.confirmed_quality_rules == [] and not payload.file_path:
        raise ValueError(
            "confirmed_quality_rules, workflow_result, execution_ready_package, or file_path is required."
        )

    builder = ExecutionPackageBuilder()
    package = builder.build_package(
        confirmed_rules,
        profile_name=payload.profile_name or "quality_package_only_from_confirmed",
        trace_metadata={"api_route": "execution_ready_package"},
    )
    return package, confirmed_rules


@router.post("/build-execution-ready-package")
def build_execution_ready_package_route(
    payload: ExecutionPackageBuildRequest,
) -> dict[str, object]:
    """Build an execution-ready governance package from confirmed quality rules."""
    try:
        package, confirmed_rules = _resolve_execution_ready_package_from_payload(payload)
        summary = ExecutionPackageBuilder.summarize_package(package)
        return {
            "message": "Execution-ready governance package was built successfully.",
            "confirmed_rule_count": len(confirmed_rules),
            "execution_ready_package": package.model_dump(),
            "execution_package_summary": summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export-execution-ready-package")
def export_execution_ready_package_route(
    payload: ExecutionPackageExportRequest,
) -> dict[str, object]:
    """Export an execution-ready governance package."""
    try:
        package, confirmed_rules = _resolve_execution_ready_package_from_payload(payload)
        output_dir = Path(
            payload.output_dir or PROJECT_ROOT / "outputs" / "execution_packages"
        )
        base_filename = payload.base_filename or (
            f"execution_ready_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        normalized_format = {
            "json": "package_json",
            "package_json": "package_json",
            "manifest": "package_manifest",
            "package_manifest": "package_manifest",
            "dbt": "dbt_yaml",
            "dbt_yaml": "dbt_yaml",
            "yaml": "dbt_yaml",
            "all": "all",
            "both": "all",
        }.get(payload.export_format.lower(), payload.export_format.lower())

        adapter = RuleExportAdapter()
        export_results: list[ExecutionPackageExportResult] = []
        if normalized_format in {"package_json", "all"}:
            export_results.append(
                adapter.export_execution_ready_package_json(
                    package,
                    str(output_dir / f"{base_filename}.json"),
                )
            )
        if normalized_format in {"package_manifest", "all"}:
            export_results.append(
                adapter.export_execution_ready_package_manifest(
                    package,
                    str(output_dir / f"{base_filename}_manifest.json"),
                )
            )
        if normalized_format in {"dbt_yaml", "all"}:
            dbt_result = adapter.export_dbt_tests_yaml(
                package,
                str(output_dir / f"{base_filename}_dbt.yml"),
            )
            export_results.append(
                ExecutionPackageExportResult(
                    export_format=dbt_result.export_format,
                    output_path=dbt_result.output_path,
                    package_id=package.package_id,
                    rule_count=dbt_result.rule_count,
                    status=dbt_result.status,
                    message=dbt_result.message,
                )
            )
        if not export_results:
            raise ValueError(
                "export_format must be one of json, package_json, manifest, package_manifest, dbt, dbt_yaml, yaml, all, or both."
            )

        return {
            "message": "Execution-ready governance package was exported successfully.",
            "package_id": package.package_id,
            "package_rule_count": package.rule_count,
            "confirmed_rule_count": len(confirmed_rules),
            "execution_package_export_results": [
                result.model_dump() for result in export_results
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/assess-governance-readiness")
def assess_governance_readiness_route(
    payload: GovernanceReadinessAssessmentRequest,
) -> dict[str, object]:
    """Assess governance readiness scores and classify gaps."""
    return call_tool_and_expand(
        "assess_governance_readiness",
        payload.model_dump(exclude_none=True),
    )


@router.post("/build-governance-work-package")
def build_governance_work_package_route(
    payload: GovernanceWorkPackageBuildRequest,
) -> dict[str, object]:
    """Build remediation actions and a governance work package."""
    return call_tool_and_expand(
        "build_governance_work_package",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-readiness-summary")
def governance_readiness_summary_route() -> dict[str, object]:
    """Return a lightweight description of readiness/remediation capability."""
    return {
        "message": "Use POST /jobs/assess-governance-readiness or /jobs/build-governance-work-package with workflow_result or file_path.",
        "dimensions": [
            "metadata_readiness",
            "mapping_readiness",
            "stg_readiness",
            "quality_rule_readiness",
            "review_completion_readiness",
        ],
    }


@router.post("/build-governance-backlog")
def build_governance_backlog_route(
    payload: GovernanceBacklogBuildRequest,
) -> dict[str, object]:
    """Build local governance backlog items."""
    return call_tool_and_expand(
        "build_governance_backlog",
        payload.model_dump(exclude_none=True),
    )


@router.post("/export-confirmation-workbooks")
def export_confirmation_workbooks_route(
    payload: GovernanceDeliveryPackageRequest,
) -> dict[str, object]:
    """Export local confirmation workbooks for governance review."""
    return call_tool_and_expand(
        "export_confirmation_workbooks",
        payload.model_dump(exclude_none=True),
    )


@router.post("/build-governance-delivery-package")
def build_governance_delivery_package_route(
    payload: GovernanceDeliveryPackageRequest,
) -> dict[str, object]:
    """Build a local governance delivery package with manifest and workbooks."""
    return call_tool_and_expand(
        "build_governance_delivery_package",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-delivery-manifest")
def governance_delivery_manifest_route() -> dict[str, object]:
    """Return a lightweight description of governance delivery package outputs."""
    return {
        "message": "Use POST /jobs/build-governance-delivery-package to generate a local package manifest.",
        "supported_artifacts": [
            "mapping_confirmation_workbook",
            "stg_confirmation_workbook",
            "quality_rule_confirmation_workbook",
            "backlog_workbook",
            "package_manifest",
        ],
        "boundary": "Local export only. No external distribution is triggered.",
    }


@router.post("/run-batch-governance")
def run_batch_governance_route(payload: BatchGovernanceRequest) -> dict[str, object]:
    """Run multi-file batch governance."""
    return call_tool_and_wrap(
        "run_batch_governance",
        payload.model_dump(exclude_none=True),
    )


@router.post("/run-incremental-rerun")
def run_incremental_rerun_route(payload: BatchGovernanceRequest) -> dict[str, object]:
    """Run changed-only batch governance."""
    return call_tool_and_wrap(
        "run_incremental_rerun",
        payload.model_dump(exclude_none=True),
    )


@router.post("/compare-governance-snapshots")
def compare_governance_snapshots_route(
    payload: BatchSnapshotCompareRequest,
) -> dict[str, object]:
    """Compare local governance batch snapshots."""
    return call_tool_and_expand(
        "compare_governance_snapshots",
        payload.model_dump(exclude_none=True),
    )


@router.get("/batch-snapshots/{batch_name}")
def batch_snapshots_route(batch_name: str) -> dict[str, object]:
    """List local batch snapshots for one batch name."""
    return {
        "batch_name": batch_name,
        "snapshots": list_batch_snapshots(batch_name),
    }


@router.post("/validate-confirmation-workbook")
def validate_confirmation_workbook_route(
    payload: ConfirmationWorkbookImportRequest,
) -> dict[str, object]:
    """Validate one confirmation workbook before import."""
    from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter

    result = ConfirmationWorkbookImporter().validate_workbook(
        payload.file_path,
        payload.workbook_type,
    )
    return {"validation_result": result.model_dump()}


@router.post("/import-confirmation-workbook")
def import_confirmation_workbook_route(
    payload: ConfirmationWorkbookImportRequest,
) -> dict[str, object]:
    """Import one filled confirmation workbook and merge local updates."""
    return call_tool_and_wrap(
        "import_confirmation_workbook",
        payload.model_dump(exclude_none=True),
        success_statuses={"success", "partial_success"},
    )


@router.post("/import-confirmation-and-rerun")
def import_confirmation_and_rerun_route(
    payload: ConfirmationWorkbookImportRequest,
) -> dict[str, object]:
    """Import one confirmation workbook and prepare changed-object rerun scope."""
    return call_tool_and_wrap(
        "import_confirmation_and_rerun",
        payload.model_dump(exclude_none=True),
        success_statuses={"success", "partial_success"},
    )


@router.get("/roundtrip-changed-objects-summary")
def roundtrip_changed_objects_summary_route() -> dict[str, object]:
    """Return a lightweight description of round-trip changed object output."""
    return {
        "message": "Round-trip changed objects are returned by import-confirmation-workbook and import-confirmation-and-rerun.",
        "summary_fields": ["changed_object_count", "changed_object_keys", "by_workbook_type"],
    }


@router.get("/governance-backlog")
def governance_backlog_route(
    status: str | None = None,
    priority: str | None = None,
    owner_role: str | None = None,
    gap_type: str | None = None,
) -> dict[str, object]:
    """List persisted governance backlog items with optional filters."""
    arguments = {
        key: value
        for key, value in {
            "status": status,
            "priority": priority,
            "owner_role": owner_role,
            "gap_type": gap_type,
        }.items()
        if value is not None
    }
    response = call_tool(
        ToolCallRequest(
            tool_name="list_governance_backlog_items",
            arguments=arguments,
        )
    )
    if response.status != "success":
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "message": response.message,
        "trace_id": response.trace_id,
        **(response.result or {}),
    }


@router.post("/governance-backlog/{backlog_id}/status")
def update_governance_backlog_status_route(
    backlog_id: str,
    payload: GovernanceBacklogStatusUpdateRequest,
) -> dict[str, object]:
    """Update one persisted backlog item status."""
    response = call_tool(
        ToolCallRequest(
            tool_name="update_governance_backlog_status",
            arguments={
                "backlog_id": backlog_id,
                "new_status": payload.new_status,
                "note": payload.note,
            },
        )
    )
    if response.status != "success":
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "message": response.message,
        "trace_id": response.trace_id,
        "update_result": response.result,
    }


@router.get("/governance-backlog-summary")
def governance_backlog_summary_route() -> dict[str, object]:
    """Return persisted governance backlog summary counts."""
    response = call_tool(
        ToolCallRequest(
            tool_name="list_governance_backlog_items",
            arguments={},
        )
    )
    if response.status != "success":
        raise HTTPException(status_code=400, detail=response.message)
    result = response.result or {}
    return {
        "message": "Governance backlog summary was loaded successfully.",
        "trace_id": response.trace_id,
        "backlog_summary": result.get("backlog_summary", {}),
    }


@router.post("/assess-governance-portfolio")
def assess_governance_portfolio_route(
    payload: GovernancePortfolioAssessmentRequest,
) -> dict[str, object]:
    """Assess backlog SLA, portfolio summary, and progress snapshot outputs."""
    return call_tool_and_expand(
        "assess_governance_portfolio",
        payload.model_dump(exclude_none=True),
    )


@router.post("/generate-progress-snapshot")
def generate_progress_snapshot_route(
    payload: ProgressSnapshotRequest,
) -> dict[str, object]:
    """Generate and optionally save a governance progress snapshot."""
    return call_tool_and_expand(
        "generate_progress_snapshot",
        payload.model_dump(exclude_none=True),
    )


@router.get("/governance-progress-snapshots")
def governance_progress_snapshots_route() -> dict[str, object]:
    """List saved governance progress snapshots."""
    return call_tool_and_expand(
        "list_governance_progress_snapshots",
        {},
    )


@router.get("/governance-portfolio-summary")
def governance_portfolio_summary_route() -> dict[str, object]:
    """Return portfolio summary for persisted backlog items."""
    response = call_tool_or_400("assess_governance_portfolio", {})
    result = response.result or {}
    return {
        "message": "Governance portfolio summary was loaded successfully.",
        "trace_id": response.trace_id,
        "governance_portfolio_summary": result.get("governance_portfolio_summary", {}),
    }


@router.get("/execution-package-summary")
def execution_package_summary_route() -> dict[str, object]:
    """Return a lightweight description of the execution-ready package capability."""
    return {
        "message": "Use POST /jobs/build-execution-ready-package with confirmed rules or file_path to build a package summary.",
        "supported_export_formats": ["package_json", "package_manifest", "dbt_yaml"],
    }


@router.get("/quality-rule-review-summary")
def quality_rule_review_summary_route() -> dict[str, object]:
    """Return quality rule review counts from stored overrides."""
    records = load_quality_rule_overrides()
    return summarize_quality_rule_review_records(records, confirmed_count=0)
