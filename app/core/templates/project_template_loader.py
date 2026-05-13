"""Load project template profiles from configuration."""

from functools import lru_cache

from app.core.models.project_template_profile import ProjectTemplateProfile
from app.core.rules.config_loader import get_project_template_profiles_config


@lru_cache(maxsize=1)
def load_project_templates() -> list[ProjectTemplateProfile]:
    """Load all configured project templates."""
    config = get_project_template_profiles_config()
    return [
        ProjectTemplateProfile.model_validate(item)
        for item in config.get("templates", [])
    ]


def list_enabled_project_templates() -> list[ProjectTemplateProfile]:
    """Return enabled project templates."""
    return [template for template in load_project_templates() if template.enabled]


def get_project_template(template_name: str) -> ProjectTemplateProfile:
    """Return one project template by name."""
    for template in load_project_templates():
        if template.template_name == template_name:
            return template
    raise ValueError(f"Project template '{template_name}' was not found.")

