"""Tests for adapter-layer manifest service helpers."""

from app.core.adapters.manifest_service import (
    get_capability_manifest,
    get_mcp_style_manifest,
    get_native_tool_schemas,
    get_openai_tool_schemas,
)


def test_manifest_service_returns_capability_manifest() -> None:
    manifest = get_capability_manifest()

    assert manifest.service_name == "data_governance_skills"
    assert manifest.tools


def test_manifest_service_returns_native_tool_schemas() -> None:
    schemas = get_native_tool_schemas()

    assert schemas
    assert any(schema.tool_name == "run_governance_profile" for schema in schemas)


def test_manifest_service_returns_openai_tool_schemas() -> None:
    schemas = get_openai_tool_schemas()

    assert schemas
    assert any(schema["function"]["name"] == "run_governance_profile" for schema in schemas)


def test_manifest_service_returns_mcp_style_manifest() -> None:
    manifest = get_mcp_style_manifest()

    assert "tools" in manifest
    assert any(tool["name"] == "publish_config_asset" for tool in manifest["tools"])
