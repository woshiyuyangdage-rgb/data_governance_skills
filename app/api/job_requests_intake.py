"""Intake and template request models."""

from pydantic import BaseModel


class DomainPackMatchRequest(BaseModel):
    """Request body for matching a domain governance pack."""

    text: str


class ProjectTemplateRunRequest(BaseModel):
    """Request body for running a project template."""

    template_name: str
    file_path: str
    domain_pack_name: str | None = None
    output_dir: str | None = None


class MetadataIntakeRequest(BaseModel):
    """Request body for metadata intake diagnosis and normalization."""

    file_path: str
    intake_profile_name: str | None = None
    sheet_name: str | None = None
    profile_name: str = "metadata_diagnosis_only"


class ConfirmationTemplateRequest(BaseModel):
    """Request body for template-aware confirmation workbook import."""

    file_path: str
    workbook_type: str | None = None
    confirmation_template_name: str | None = None
    sheet_name: str | None = None
    rerun_changed_only: bool = True
