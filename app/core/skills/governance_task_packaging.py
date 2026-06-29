"""Compatibility wrapper for metadata diagnosis skill modules."""

from app.core.skills.metadata_diagnosis_skill.governance_task_packaging import (
    GovernanceTaskPackagingInput,
    GovernanceTaskPackagingOutput,
    GovernanceTaskPackagingSkill,
)

__all__ = [
    "GovernanceTaskPackagingInput",
    "GovernanceTaskPackagingOutput",
    "GovernanceTaskPackagingSkill",
]
