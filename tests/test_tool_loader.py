"""Tests for the local governance tool registry."""

import pytest

from app.core.tools.tool_exceptions import ToolNotFoundError
from app.core.tools.tool_loader import (
    get_tool_definition,
    list_enabled_tools,
    load_tool_registry,
)


def test_tool_registry_loads_enabled_tools() -> None:
    definitions = load_tool_registry()
    enabled = list_enabled_tools()

    assert definitions
    assert enabled
    assert any(tool.name == "run_governance_profile" for tool in enabled)
    assert any(tool.name == "list_config_assets" for tool in enabled)
    assert any(tool.name == "recommend_quality_rules" for tool in enabled)
    assert any(tool.name == "recommend_quality_intelligence" for tool in enabled)
    assert any(tool.name == "batch_review_quality_rules" for tool in enabled)
    assert any(tool.name == "build_execution_ready_package" for tool in enabled)
    assert any(tool.name == "learning_health" for tool in enabled)
    assert any(tool.name == "rebuild_review_learning" for tool in enabled)


def test_get_tool_definition_returns_expected_tool() -> None:
    definition = get_tool_definition("preview_agent_plan")

    assert definition.handler == "governance_tool_executor.preview_agent_plan"
    assert definition.enabled is True


def test_get_tool_definition_returns_learning_memory_tool() -> None:
    definition = get_tool_definition("rebuild_review_learning")

    assert definition.handler == "governance_tool_executor.rebuild_review_learning"
    assert definition.input_model == "ReviewLearningRebuildArguments"
    assert definition.category == "learning_memory"
    assert definition.enabled is True


def test_get_tool_definition_raises_for_missing_tool() -> None:
    with pytest.raises(ToolNotFoundError):
        get_tool_definition("missing_tool")
