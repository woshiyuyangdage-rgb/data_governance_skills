"""Metadata diagnosis product skill package."""

from app.core.skills.metadata_diagnosis_skill.governance_task_packaging import (
    GovernanceTaskPackagingInput,
    GovernanceTaskPackagingOutput,
    GovernanceTaskPackagingSkill,
)
from app.core.skills.metadata_diagnosis_skill.metadata_completeness_check import (
    MetadataCompletenessCheckSkill,
    MetadataCompletenessInput,
    MetadataCompletenessOutput,
)
from app.core.skills.metadata_diagnosis_skill.metadata_quality_diagnosis import (
    MetadataQualityDiagnosisInput,
    MetadataQualityDiagnosisOutput,
    MetadataQualityDiagnosisSkill,
)
from app.core.skills.metadata_diagnosis_skill.naming_standard_check import (
    NamingStandardCheckInput,
    NamingStandardCheckOutput,
    NamingStandardCheckSkill,
)
from app.core.skills.metadata_diagnosis_skill.technical_object_identification import (
    TechnicalObjectIdentificationInput,
    TechnicalObjectIdentificationOutput,
    TechnicalObjectIdentificationSkill,
)

__all__ = [
    "GovernanceTaskPackagingInput",
    "GovernanceTaskPackagingOutput",
    "GovernanceTaskPackagingSkill",
    "MetadataCompletenessCheckSkill",
    "MetadataCompletenessInput",
    "MetadataCompletenessOutput",
    "MetadataQualityDiagnosisInput",
    "MetadataQualityDiagnosisOutput",
    "MetadataQualityDiagnosisSkill",
    "NamingStandardCheckInput",
    "NamingStandardCheckOutput",
    "NamingStandardCheckSkill",
    "TechnicalObjectIdentificationInput",
    "TechnicalObjectIdentificationOutput",
    "TechnicalObjectIdentificationSkill",
]
