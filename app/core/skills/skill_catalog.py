"""Load product-level governance skill catalog definitions."""

from functools import lru_cache

from app.core.models.skill_definition import SkillDefinition
from app.core.rules.config_loader import load_yaml_config


@lru_cache(maxsize=1)
def load_skill_catalog() -> list[SkillDefinition]:
    """Load configured product-level skills from skill_registry.yaml."""
    config = load_yaml_config("skill_registry.yaml")
    skills_data = config.get("skills", [])
    if not isinstance(skills_data, list):
        raise ValueError("skill_registry.yaml must contain a 'skills' list.")

    definitions: list[SkillDefinition] = []
    for item in skills_data:
        if not isinstance(item, dict):
            raise ValueError("Each skill entry must be a mapping.")
        definitions.append(SkillDefinition(**item))
    return definitions


def list_enabled_skills() -> list[SkillDefinition]:
    """Return enabled product-level governance skills."""
    return [definition for definition in load_skill_catalog() if definition.enabled]
