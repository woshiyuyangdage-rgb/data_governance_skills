"""Project template run result model."""

from pydantic import BaseModel, Field


class ProjectTemplateRunResult(BaseModel):
    """Summary of a project template application."""

    template_name: str
    selected_domain_pack: str | None = None
    applied_defaults: dict = Field(default_factory=dict)
    workflow_profile: str | None = None
    status: str
    message: str | None = None

