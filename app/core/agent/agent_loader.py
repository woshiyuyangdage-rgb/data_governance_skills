"""Load lightweight agent shell configuration."""

from functools import lru_cache

from app.core.agent.agent_exceptions import AgentShellConfigError
from app.core.rules.config_loader import load_yaml_config


@lru_cache(maxsize=1)
def load_agent_shell_config() -> dict[str, object]:
    """Load and validate agent shell configuration."""
    try:
        config = load_yaml_config("agent_shell.yaml")
    except FileNotFoundError as exc:
        raise AgentShellConfigError(
            "agent_shell.yaml is missing from app/config."
        ) from exc

    if not isinstance(config.get("confirmation_policy", {}), dict):
        raise AgentShellConfigError(
            "agent_shell.yaml must contain a confirmation_policy mapping."
        )
    if not isinstance(config.get("validation_policy", {}), dict):
        raise AgentShellConfigError(
            "agent_shell.yaml must contain a validation_policy mapping."
        )
    if not isinstance(config.get("session_policy", {}), dict):
        raise AgentShellConfigError(
            "agent_shell.yaml must contain a session_policy mapping."
        )
    if not isinstance(config.get("default_behavior", {}), dict):
        raise AgentShellConfigError(
            "agent_shell.yaml must contain a default_behavior mapping."
        )

    return config
