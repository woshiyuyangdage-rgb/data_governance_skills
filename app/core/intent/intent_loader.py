"""Load rule-based intent interpretation patterns from configuration."""

from functools import lru_cache

from app.core.intent.intent_exceptions import IntentConfigError
from app.core.rules.config_loader import load_yaml_config


@lru_cache(maxsize=1)
def load_intent_patterns() -> dict[str, object]:
    """Load and validate intent pattern configuration."""
    try:
        config = load_yaml_config("intent_patterns.yaml")
    except FileNotFoundError as exc:
        raise IntentConfigError(
            "intent_patterns.yaml is missing from app/config."
        ) from exc

    intents = config.get("intents")
    parameters = config.get("parameters")
    if not isinstance(intents, dict):
        raise IntentConfigError(
            "intent_patterns.yaml must contain an 'intents' mapping."
        )
    if not isinstance(parameters, dict):
        raise IntentConfigError(
            "intent_patterns.yaml must contain a 'parameters' mapping."
        )

    for intent_name, payload in intents.items():
        if not isinstance(payload, dict):
            raise IntentConfigError(
                f"Intent definition '{intent_name}' must be a mapping."
            )
        if not isinstance(payload.get("keywords", []), list):
            raise IntentConfigError(
                f"Intent definition '{intent_name}' must contain a keywords list."
            )

    for parameter_name, payload in parameters.items():
        if not isinstance(payload, dict):
            raise IntentConfigError(
                f"Parameter definition '{parameter_name}' must be a mapping."
            )
        if not isinstance(payload.get("keywords", []), list):
            raise IntentConfigError(
                f"Parameter definition '{parameter_name}' must contain a keywords list."
            )

    return config


def get_intent_definitions() -> dict[str, dict[str, object]]:
    """Return configured intent definitions."""
    config = load_intent_patterns()
    return dict(config.get("intents", {}))


def get_parameter_definitions() -> dict[str, dict[str, object]]:
    """Return configured parameter definitions."""
    config = load_intent_patterns()
    return dict(config.get("parameters", {}))
