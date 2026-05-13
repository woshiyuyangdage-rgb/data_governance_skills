"""Delivery layout adaptation result model."""

from pydantic import BaseModel, Field


class DeliveryLayoutResult(BaseModel):
    """Summary of one applied delivery layout profile."""

    template_name: str
    layout_spec_name: str
    target_artifact_type: str
    applied_sheet_name: str | None = None
    applied_columns: list[str] = Field(default_factory=list)
    extra_columns_added: list[str] = Field(default_factory=list)
    status: str
    message: str | None = None
