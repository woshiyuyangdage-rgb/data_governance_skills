"""Tests for rule-based intent pattern loading."""

from app.core.intent.intent_loader import (
    get_intent_definitions,
    get_parameter_definitions,
    load_intent_patterns,
)


def test_intent_patterns_can_be_loaded() -> None:
    config = load_intent_patterns()

    assert "intents" in config
    assert "parameters" in config


def test_intent_and_parameter_definitions_exist() -> None:
    intents = get_intent_definitions()
    parameters = get_parameter_definitions()

    assert "quick_scan" in intents
    assert "standard_recommendation" in intents
    assert intents["quick_scan"]["profile_name"] == "metadata_diagnosis_only"
    assert "export_reports" in parameters
    assert isinstance(parameters["export_reports"]["keywords"], list)
