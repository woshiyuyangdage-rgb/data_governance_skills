"""Load local context resolution configuration."""

from functools import lru_cache

from app.core.context.context_exceptions import ContextResolutionConfigError
from app.core.rules.config_loader import load_yaml_config


@lru_cache(maxsize=1)
def load_context_resolution_config() -> dict[str, object]:
    """Load and validate context resolution configuration."""
    try:
        config = load_yaml_config("context_resolution.yaml")
    except FileNotFoundError as exc:
        raise ContextResolutionConfigError(
            "context_resolution.yaml is missing from app/config."
        ) from exc

    if not isinstance(config.get("file_resolution_priority", []), list):
        raise ContextResolutionConfigError(
            "context_resolution.yaml must contain a file_resolution_priority list."
        )
    if not isinstance(config.get("supported_file_references", []), list):
        raise ContextResolutionConfigError(
            "context_resolution.yaml must contain a supported_file_references list."
        )
    if not isinstance(config.get("supported_result_references", []), list):
        raise ContextResolutionConfigError(
            "context_resolution.yaml must contain a supported_result_references list."
        )
    if not isinstance(config.get("autofill_policy", {}), dict):
        raise ContextResolutionConfigError(
            "context_resolution.yaml must contain an autofill_policy mapping."
        )
    if not isinstance(config.get("ambiguity_policy", {}), dict):
        raise ContextResolutionConfigError(
            "context_resolution.yaml must contain an ambiguity_policy mapping."
        )

    return config
