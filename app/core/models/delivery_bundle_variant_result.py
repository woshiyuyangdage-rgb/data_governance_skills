"""Delivery bundle variant result model."""

from pydantic import BaseModel, Field


class DeliveryBundleVariantResult(BaseModel):
    """Summary of one applied delivery bundle variant."""

    variant_name: str
    included_outputs: list[str] = Field(default_factory=list)
    generated_files: dict = Field(default_factory=dict)
    status: str
    message: str | None = None
