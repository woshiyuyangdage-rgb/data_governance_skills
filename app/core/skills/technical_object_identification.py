"""Compatibility wrapper for metadata diagnosis skill modules."""

from app.core.skills.metadata_diagnosis_skill.technical_object_identification import (
    TechnicalObjectIdentificationInput,
    TechnicalObjectIdentificationOutput,
    TechnicalObjectIdentificationSkill,
)

__all__ = [
    "TechnicalObjectIdentificationInput",
    "TechnicalObjectIdentificationOutput",
    "TechnicalObjectIdentificationSkill",
]
