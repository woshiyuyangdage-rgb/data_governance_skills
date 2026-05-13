"""Project template profile model."""

from pydantic import BaseModel, Field


class ProjectTemplateProfile(BaseModel):
    """Project-oriented preset over an existing workflow profile."""

    template_name: str
    enabled: bool
    description: str
    base_workflow_profile: str
    default_outputs: list[str] = Field(default_factory=list)
    default_domain_pack: str | None = None
    default_review_mode: bool = False

