"""Tests for adapter-layer configuration loading."""

from app.core.adapters.adapter_loader import load_adapter_config


def test_adapter_config_loads_with_expected_sections() -> None:
    config = load_adapter_config()

    assert "manifest" in config
    assert "schema_export" in config
    assert "invocation_policy" in config
    assert "compatibility" in config
    assert config["manifest"]["service_name"] == "data_governance_skills"
