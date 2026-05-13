"""Domain governance pack model."""

from pydantic import BaseModel, Field


class DomainGovernancePack(BaseModel):
    """Reusable rule-based hints for one governance domain."""

    pack_name: str
    enabled: bool
    description: str
    trigger_tokens: list[str] = Field(default_factory=list)
    preferred_group_by: str | None = None
    default_owner_roles: dict = Field(default_factory=dict)
    mapping_hints: dict = Field(default_factory=dict)
    quality_rule_hints: dict = Field(default_factory=dict)
    cross_field_hints: dict = Field(default_factory=dict)
    remediation_hints: dict = Field(default_factory=dict)

