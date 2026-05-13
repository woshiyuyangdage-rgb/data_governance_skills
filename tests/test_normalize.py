"""Tests for normalization helpers."""

from app.core.normalize.abbreviation_expander import (
    expand_tokens,
    expand_tokens_with_evidence,
    normalize_tokens,
)
from app.core.normalize.text_cleaner import clean_text
from app.core.normalize.token_splitter import split_tokens


def test_split_tokens_handles_underscore_space_and_camel_case() -> None:
    assert split_tokens("cust_amt_dt") == ["cust", "amt", "dt"]
    assert split_tokens("Cust ID") == ["cust", "id"]
    assert split_tokens("customerCreatedDate") == ["customer", "created", "date"]
    assert split_tokens("ORDER_STATUS_CODE") == ["order", "status", "code"]


def test_expand_tokens_and_normalize_tokens_use_knowledge_packs() -> None:
    tokens = ["cust", "amt", "dt"]

    assert expand_tokens(tokens) == ["customer", "amount", "date"]
    assert normalize_tokens(["customer", "amount", "date"]) == [
        "customer",
        "amount",
        "date",
    ]

    expanded_tokens, expanded_pairs, evidence = expand_tokens_with_evidence(tokens)
    assert expanded_tokens == ["customer", "amount", "date"]
    assert expanded_pairs
    assert evidence


def test_clean_text_collapses_whitespace_and_separators() -> None:
    assert clean_text("  Cust/ID  -  Main  ") == "cust id main"
