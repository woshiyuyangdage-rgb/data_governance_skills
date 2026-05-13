"""Configuration status model for local control plane assets."""

from pydantic import BaseModel


class ConfigStatus(BaseModel):
    """Track validation and publish status for one managed asset."""

    asset_name: str
    asset_type: str | None = None
    file_path: str | None = None
    current_status: str
    last_validated_at: str | None = None
    last_published_at: str | None = None
    last_error_message: str | None = None
