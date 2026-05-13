"""Tool definition metadata for the local governance tool layer."""

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Describe one callable local governance tool."""

    name: str
    enabled: bool = True
    description: str
    input_model: str
    output_model: str
    handler: str
    category: str
