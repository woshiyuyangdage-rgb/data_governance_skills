"""Core workflow and intent job routes."""

from fastapi import APIRouter

from app.api.job_catalog import build_job_catalog
from app.api.job_requests import FileRunRequest, IntentTextRequest
from app.core.intent.intent_task_service import (
    interpret_and_build_request,
    interpret_and_run_task,
)
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.models.workflow_profile import WorkflowProfile
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_mapping_only_from_file,
    run_p0_pipeline_from_file,
    run_p0_plus_mapping_from_file,
    run_p0_plus_mapping_plus_stg_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
    run_p0_plus_mapping_plus_stg_with_review_from_file,
    run_quality_only_from_stg_from_file,
    run_quality_only_from_stg_with_review_from_file,
    run_stg_only_from_mapping_from_file,
)
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.orchestrator.task_service import run_governance_task
from app.core.orchestrator.workflow_engine import WorkflowEngine

router = APIRouter()


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
def run_p0_plus_mapping_plus_stg_with_review(
    payload: FileRunRequest,
) -> WorkflowResult:
    """Run the rule-based workflow with saved review overrides applied."""
    return run_p0_plus_mapping_plus_stg_with_review_from_file(payload.file_path)


@router.post("/run-p0-plus-mapping-plus-stg-plus-quality", response_model=WorkflowResult)
def run_p0_plus_mapping_plus_stg_plus_quality(
    payload: FileRunRequest,
) -> WorkflowResult:
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
def run_quality_only_from_stg_with_review(
    payload: FileRunRequest,
) -> WorkflowResult:
    """Run mapping, STG, quality, and review replay without full diagnosis packaging."""
    return run_quality_only_from_stg_with_review_from_file(payload.file_path)


@router.post("/run-governance-task", response_model=GovernanceTaskResponse)
def run_governance_task_route(
    payload: GovernanceTaskRequest,
) -> GovernanceTaskResponse:
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
def run_interpreted_governance_task(
    payload: IntentTextRequest,
) -> IntentExecutionResult:
    """Interpret task text and execute it through the governance router."""
    return interpret_and_run_task(payload.text, payload.file_path)
