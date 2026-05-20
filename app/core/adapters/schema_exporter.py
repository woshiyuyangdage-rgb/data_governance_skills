"""Export local governance tools into adapter-friendly schema formats."""

from app.core.adapters.adapter_loader import load_adapter_config
from app.core.adapters.schema_export_definitions import (
    MODEL_SCHEMA_MAP,
    TOOL_EXAMPLES,
)
from app.core.models.capability_manifest import CapabilityManifest
from app.core.models.exported_tool_schema import ExportedToolSchema
from app.core.tools.tool_loader import load_tool_registry
from app.core.utils.time_utils import utc_now_seconds


def _utc_now() -> str:
    return utc_now_seconds()


class SchemaExporter:
    """Export local tool definitions into adapter-ready schema formats."""

    def __init__(self) -> None:
        self.config = load_adapter_config()

    def _include_disabled_tools(self) -> bool:
        schema_export = self.config.get("schema_export", {})
        return bool(schema_export.get("include_disabled_tools", False))

    def _include_examples(self) -> bool:
        schema_export = self.config.get("schema_export", {})
        return bool(schema_export.get("include_examples", True))

    def _compatibility_enabled(self, key: str, default: bool = True) -> bool:
        compatibility = self.config.get("compatibility", {})
        return bool(compatibility.get(key, default))

    def _tool_definitions(self):
        definitions = load_tool_registry()
        if self._include_disabled_tools():
            return definitions
        return [definition for definition in definitions if definition.enabled]

    @staticmethod
    def _lookup_schema(model_name: str) -> dict[str, object]:
        return dict(MODEL_SCHEMA_MAP.get(model_name, {"type": "object"}))

    def _build_native_schema(self, definition) -> ExportedToolSchema:
        return ExportedToolSchema(
            tool_name=definition.name,
            description=definition.description,
            input_model=definition.input_model,
            output_model=definition.output_model,
            category=definition.category,
            input_schema=self._lookup_schema(definition.input_model),
            output_schema=self._lookup_schema(definition.output_model),
            examples=list(TOOL_EXAMPLES.get(definition.name, []))
            if self._include_examples()
            else [],
        )

    def export_native_tool_schemas(self) -> list[ExportedToolSchema]:
        """Return native tool schemas derived from the tool registry."""
        return [
            self._build_native_schema(definition)
            for definition in self._tool_definitions()
        ]

    def export_openai_style_schemas(self) -> list[dict[str, object]]:
        """Return simplified OpenAI-style function schemas."""
        if not self._compatibility_enabled("export_openai_style_schema", True):
            return []
        schemas: list[dict[str, object]] = []
        for native_schema in self.export_native_tool_schemas():
            schema_payload: dict[str, object] = {
                "type": "function",
                "function": {
                    "name": native_schema.tool_name,
                    "description": native_schema.description,
                    "parameters": native_schema.input_schema,
                },
            }
            if self._include_examples() and native_schema.examples:
                schema_payload["examples"] = native_schema.examples
            schemas.append(schema_payload)
        return schemas

    def export_mcp_style_manifest(self) -> dict[str, object]:
        """Return a lightweight local MCP-style manifest structure."""
        if not self._compatibility_enabled("export_mcp_style_manifest", True):
            return {"service": {}, "tools": [], "generated_at": _utc_now()}
        manifest_config = self.config.get("manifest", {})
        tools: list[dict[str, object]] = []
        for native_schema in self.export_native_tool_schemas():
            tool_payload: dict[str, object] = {
                "name": native_schema.tool_name,
                "description": native_schema.description,
                "inputSchema": native_schema.input_schema,
                "annotations": {
                    "category": native_schema.category,
                    "outputSchema": native_schema.output_schema,
                },
            }
            if self._include_examples() and native_schema.examples:
                tool_payload["examples"] = native_schema.examples
            tools.append(tool_payload)

        return {
            "service": {
                "name": manifest_config.get("service_name", "data_governance_skills"),
                "version": manifest_config.get("version", "v1"),
                "description": manifest_config.get(
                    "description",
                    "Local governance tool platform",
                ),
            },
            "tools": tools,
            "generated_at": _utc_now(),
        }

    def build_capability_manifest(self) -> CapabilityManifest:
        """Build one summarized capability manifest for external adapter consumers."""
        manifest_config = self.config.get("manifest", {})
        tools = [
            {
                "name": schema.tool_name,
                "description": schema.description,
                "category": schema.category,
                "input_model": schema.input_model,
                "output_model": schema.output_model,
                "input_schema": schema.input_schema,
                "output_schema": schema.output_schema,
            }
            for schema in self.export_native_tool_schemas()
        ]
        return CapabilityManifest(
            service_name=str(
                manifest_config.get("service_name", "data_governance_skills")
            ),
            version=str(manifest_config.get("version", "v1")),
            description=str(
                manifest_config.get("description", "Local governance tool platform")
            ),
            tools=tools,
            generated_at=_utc_now(),
        )


# TODO: extend schema export with richer model reflection once a real external protocol binding needs more complete JSON schema.
