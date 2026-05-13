"""Shared base class for all governance skills.

All future skills should inherit from this class to keep a consistent
interface across FastAPI, Streamlit, and workflow orchestration layers.
"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Abstract base interface for governance skills."""

    skill_name: str = "base_skill"
    version: str = "0.1.0"
    description: str = "Abstract governance skill."

    @abstractmethod
    def run(self, payload: object) -> object:
        """Execute the skill with a standardized payload."""
