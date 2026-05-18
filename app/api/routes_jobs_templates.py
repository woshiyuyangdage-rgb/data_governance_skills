"""Domain, project-template, and intake job routes."""

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    ConfirmationTemplateRequest,
    DomainPackMatchRequest,
    MetadataIntakeRequest,
    ProjectTemplateRunRequest,
)
from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter
from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.intake.intake_adapter_service import IntakeAdapterService
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.intake_match_result import IntakeMatchResult
from app.core.models.intake_normalization_result import IntakeNormalizationResult
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.templates.project_template_service import ProjectTemplateService

router = APIRouter()


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
def diagnose_metadata_intake_template(
    request: MetadataIntakeRequest,
) -> IntakeMatchResult:
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
def normalize_metadata_input(
    request: MetadataIntakeRequest,
) -> IntakeNormalizationResult:
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
def run_governance_with_intake_profile(
    request: MetadataIntakeRequest,
) -> WorkflowResult:
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


@router.post(
    "/diagnose-confirmation-template",
    response_model=ConfirmationTemplateMatchResult,
)
def diagnose_confirmation_template(
    request: ConfirmationTemplateRequest,
) -> ConfirmationTemplateMatchResult:
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
def import_confirmation_with_template(
    request: ConfirmationTemplateRequest,
) -> WorkflowResult:
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
def import_confirmation_template_and_rerun(
    request: ConfirmationTemplateRequest,
) -> WorkflowResult:
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
