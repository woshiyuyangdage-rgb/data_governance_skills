"""Compatibility wrapper for metadata diagnosis skill modules."""

from app.core.skills.metadata_diagnosis_skill.metadata_completeness_check import (
    MetadataCompletenessCheckSkill,
    MetadataCompletenessInput,
    MetadataCompletenessOutput,
)

__all__ = [
    "MetadataCompletenessCheckSkill",
    "MetadataCompletenessInput",
    "MetadataCompletenessOutput",
]
