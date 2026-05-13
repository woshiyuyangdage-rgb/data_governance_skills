"""Load and validate configured governance workflow profiles."""

from functools import lru_cache

from app.core.models.workflow_profile import WorkflowProfile
from app.core.orchestrator.profile_exceptions import (
    WorkflowProfileConfigError,
    WorkflowProfileNotFoundError,
)
from app.core.rules.config_loader import load_yaml_config


@lru_cache(maxsize=1)
def load_workflow_profiles() -> list[WorkflowProfile]:
    """Load configured workflow profiles from YAML."""
    try:
        config = load_yaml_config("workflow_profiles.yaml")
    except FileNotFoundError as exc:
        raise WorkflowProfileConfigError(
            "workflow_profiles.yaml is missing from app/config."
        ) from exc

    profiles_data = config.get("profiles", [])
    if not isinstance(profiles_data, list):
        raise WorkflowProfileConfigError(
            "workflow_profiles.yaml must contain a 'profiles' list."
        )

    profiles: list[WorkflowProfile] = []
    for item in profiles_data:
        if not isinstance(item, dict):
            raise WorkflowProfileConfigError(
                "Each workflow profile entry must be a mapping."
            )
        profiles.append(WorkflowProfile(**item))

    return profiles


def get_workflow_profile(profile_name: str) -> WorkflowProfile:
    """Return one configured workflow profile by name."""
    for profile in load_workflow_profiles():
        if profile.name == profile_name:
            return profile

    raise WorkflowProfileNotFoundError(
        f"Workflow profile '{profile_name}' was not found."
    )


def list_enabled_profiles() -> list[WorkflowProfile]:
    """Return enabled workflow profiles only."""
    return [profile for profile in load_workflow_profiles() if profile.enabled]
