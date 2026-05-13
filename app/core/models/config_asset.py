"""Managed configuration asset model for the local control plane."""

from pydantic import BaseModel


class ConfigAsset(BaseModel):
    """One configuration asset managed by the local control plane."""

    asset_name: str
    asset_type: str
    file_path: str
    description: str | None = None
    editable: bool = True
