"""Load and validate local governance tool definitions."""

from functools import lru_cache

from app.core.models.tool_definition import ToolDefinition
from app.core.rules.config_loader import load_yaml_config
from app.core.tools.tool_exceptions import ToolNotFoundError, ToolRegistryError


@lru_cache(maxsize=1)
def load_tool_registry() -> list[ToolDefinition]:
    """Load tool definitions from tool_registry.yaml."""
    try:
        config = load_yaml_config("tool_registry.yaml")
    except FileNotFoundError as exc:
        raise ToolRegistryError(
            "tool_registry.yaml is missing from app/config."
        ) from exc

    tools_data = config.get("tools", [])
    if not isinstance(tools_data, list):
        raise ToolRegistryError(
            "tool_registry.yaml must contain a 'tools' list."
        )

    definitions: list[ToolDefinition] = []
    for item in tools_data:
        if not isinstance(item, dict):
            raise ToolRegistryError("Each tool entry must be a mapping.")
        definitions.append(ToolDefinition(**item))

    return definitions


def list_enabled_tools() -> list[ToolDefinition]:
    """Return enabled tool definitions only."""
    return [definition for definition in load_tool_registry() if definition.enabled]


def get_tool_definition(tool_name: str) -> ToolDefinition:
    """Return one tool definition by name."""
    for definition in load_tool_registry():
        if definition.name == tool_name:
            return definition

    raise ToolNotFoundError(f"Tool '{tool_name}' was not found.")
