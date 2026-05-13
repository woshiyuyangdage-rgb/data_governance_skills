"""Smoke tests for rule-based domain pack matching."""

from app.core.domain.domain_pack_matcher import DomainPackMatcher


def test_domain_pack_matcher_matches_core_domains() -> None:
    matcher = DomainPackMatcher()

    assert matcher.match_domain_pack_from_text("customer profile cust_id").matched_pack_name == "customer_domain_pack"
    assert matcher.match_domain_pack_from_text("payment order transaction amount").matched_pack_name == "transaction_domain_pack"
    assert matcher.match_domain_pack_from_text("lookup dictionary status code").matched_pack_name == "reference_code_domain_pack"
    assert matcher.match_domain_pack_from_text("invoice settlement supplier finance").matched_pack_name == "supply_chain_finance_domain_pack"


def test_domain_pack_matcher_fallback() -> None:
    result = DomainPackMatcher().match_domain_pack_from_text("unrelated archive notes")
    assert result.fallback_used is True
    assert result.matched_pack_name is None

