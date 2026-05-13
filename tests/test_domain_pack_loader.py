"""Smoke tests for domain governance pack loading."""

from app.core.domain.domain_pack_loader import (
    get_domain_pack,
    list_enabled_domain_packs,
    load_domain_packs,
)


def test_domain_packs_can_load() -> None:
    packs = load_domain_packs()
    assert {pack.pack_name for pack in packs} >= {
        "customer_domain_pack",
        "transaction_domain_pack",
        "reference_code_domain_pack",
        "supply_chain_finance_domain_pack",
    }


def test_enabled_domain_pack_list_and_lookup() -> None:
    enabled = list_enabled_domain_packs()
    assert enabled
    assert get_domain_pack("customer_domain_pack").enabled is True

