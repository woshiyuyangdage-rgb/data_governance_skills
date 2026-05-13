"""Abbreviation and root-word normalization helpers."""

from functools import lru_cache

from app.core.knowledge.knowledge_loader import (
    load_abbreviation_dict,
    load_root_word_dict,
)


@lru_cache(maxsize=1)
def _build_abbreviation_map() -> dict[str, str]:
    dataframe = load_abbreviation_dict()
    return {
        str(row["abbreviation"]).strip().lower(): str(row["expanded_form"]).strip().lower()
        for _, row in dataframe.iterrows()
    }


@lru_cache(maxsize=1)
def _build_root_word_map() -> dict[str, str]:
    dataframe = load_root_word_dict()
    return {
        str(row["token"]).strip().lower(): str(row["normalized_form"]).strip().lower()
        for _, row in dataframe.iterrows()
    }


def expand_tokens(tokens: list[str]) -> list[str]:
    """Expand known abbreviations while keeping unmatched tokens unchanged."""
    abbreviation_map = _build_abbreviation_map()
    return [abbreviation_map.get(token.lower(), token.lower()) for token in tokens]


def expand_tokens_with_evidence(
    tokens: list[str],
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    """Expand abbreviations and return structured evidence for explanations."""
    abbreviation_map = _build_abbreviation_map()
    expanded_tokens: list[str] = []
    expanded_pairs: list[dict[str, str]] = []
    evidence: list[str] = []

    for token in tokens:
        lowered = token.lower()
        expanded = abbreviation_map.get(lowered, lowered)
        expanded_tokens.append(expanded)
        if expanded != lowered:
            expanded_pairs.append({"token": lowered, "expanded_form": expanded})
            evidence.append(f"expanded abbreviation '{lowered}' to '{expanded}'")

    return expanded_tokens, expanded_pairs, evidence


def normalize_tokens(tokens: list[str]) -> list[str]:
    """Normalize tokens against the root-word knowledge pack."""
    root_word_map = _build_root_word_map()
    return [root_word_map.get(token.lower(), token.lower()) for token in tokens]


def expand_abbreviation(text: str) -> str:
    """Backward-compatible alias for simple abbreviation expansion."""
    tokens = text.split("_")
    return "_".join(expand_tokens(tokens))


# TODO: extend abbreviation handling with context-aware disambiguation in a semantic version.
