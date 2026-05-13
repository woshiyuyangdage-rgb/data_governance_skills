"""Tests for context resolution configuration loading."""

from app.core.context.context_loader import load_context_resolution_config


def test_context_resolution_config_loads_with_expected_sections() -> None:
    config = load_context_resolution_config()

    assert isinstance(config.get("file_resolution_priority", []), list)
    assert isinstance(config.get("supported_file_references", []), list)
    assert isinstance(config.get("supported_result_references", []), list)
    assert isinstance(config.get("autofill_policy", {}), dict)
    assert isinstance(config.get("ambiguity_policy", {}), dict)
    assert "this file" in config.get("supported_file_references", [])
