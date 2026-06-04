"""Control-plane request models."""

from pydantic import BaseModel


class ConfigAssetSaveRequest(BaseModel):
    """Request body for saving one managed config asset."""

    content: object


class LearningMemoryClearRequest(BaseModel):
    """Request body for clearing learned memory by field key."""

    memory_type: str
    field_key: str
