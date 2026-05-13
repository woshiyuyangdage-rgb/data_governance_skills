"""Delivery template profile model."""

from pydantic import BaseModel


class DeliveryTemplateProfile(BaseModel):
    """Rule-based profile for adapting one delivery artifact layout."""

    template_name: str
    enabled: bool
    description: str
    target_artifact_type: str
    layout_spec_name: str
    include_instruction_sheet: bool = True
    include_summary_sheet: bool = True
    default_output_filename: str | None = None
