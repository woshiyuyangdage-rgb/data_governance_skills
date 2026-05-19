"""Control-plane request models."""

from pydantic import BaseModel


class ConfigAssetSaveRequest(BaseModel):
    """Request body for saving one managed config asset."""

    content: object
