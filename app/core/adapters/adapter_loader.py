"""Load adapter-layer configuration for manifest and invocation helpers."""

from functools import lru_cache

from app.core.rules.config_loader import load_yaml_config


@lru_cache(maxsize=1)
def load_adapter_config() -> dict[str, object]:
    """Load adapter-layer configuration from YAML."""
    config = load_yaml_config("adapter_layer.yaml")
    manifest = config.get("manifest")
    schema_export = config.get("schema_export")
    invocation_policy = config.get("invocation_policy")
    compatibility = config.get("compatibility")

    if not isinstance(manifest, dict):
        raise ValueError("adapter_layer.yaml must contain a 'manifest' mapping.")
    if not isinstance(schema_export, dict):
        raise ValueError("adapter_layer.yaml must contain a 'schema_export' mapping.")
    if not isinstance(invocation_policy, dict):
        raise ValueError("adapter_layer.yaml must contain an 'invocation_policy' mapping.")
    if not isinstance(compatibility, dict):
        raise ValueError("adapter_layer.yaml must contain a 'compatibility' mapping.")

    return config
