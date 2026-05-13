"""Service helpers for adapter-layer manifest and schema export."""

from app.core.adapters.schema_exporter import SchemaExporter
from app.core.models.capability_manifest import CapabilityManifest
from app.core.models.exported_tool_schema import ExportedToolSchema


def get_capability_manifest() -> CapabilityManifest:
    """Return the adapter-layer capability manifest."""
    exporter = SchemaExporter()
    return exporter.build_capability_manifest()


def get_native_tool_schemas() -> list[ExportedToolSchema]:
    """Return native adapter-layer tool schemas."""
    exporter = SchemaExporter()
    return exporter.export_native_tool_schemas()


def get_openai_tool_schemas() -> list[dict[str, object]]:
    """Return simplified OpenAI-style function schemas."""
    exporter = SchemaExporter()
    return exporter.export_openai_style_schemas()


def get_mcp_style_manifest() -> dict[str, object]:
    """Return a lightweight MCP-style manifest payload."""
    exporter = SchemaExporter()
    return exporter.export_mcp_style_manifest()


# TODO: add file export helpers once external adapter packages need serialized manifests on disk.
