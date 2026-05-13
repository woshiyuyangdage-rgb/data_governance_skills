"""Load domain governance packs from configuration."""

from functools import lru_cache

from app.core.models.domain_governance_pack import DomainGovernancePack
from app.core.rules.config_loader import get_domain_governance_packs_config


@lru_cache(maxsize=1)
def load_domain_packs() -> list[DomainGovernancePack]:
    """Load all configured domain governance packs."""
    config = get_domain_governance_packs_config()
    return [DomainGovernancePack.model_validate(item) for item in config.get("packs", [])]


def list_enabled_domain_packs() -> list[DomainGovernancePack]:
    """Return enabled domain governance packs."""
    return [pack for pack in load_domain_packs() if pack.enabled]


def get_domain_pack(pack_name: str) -> DomainGovernancePack:
    """Return one domain governance pack by name."""
    for pack in load_domain_packs():
        if pack.pack_name == pack_name:
            return pack
    raise ValueError(f"Domain governance pack '{pack_name}' was not found.")

