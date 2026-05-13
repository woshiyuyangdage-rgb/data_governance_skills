"""Text cleaning helpers for metadata normalization."""

import re

SEPARATOR_PATTERN = re.compile(r"[-./\\|]+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str | None, lower: bool = True) -> str:
    """Normalize raw metadata text before downstream checks."""
    if text is None:
        return ""

    normalized = str(text).strip()
    normalized = SEPARATOR_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    if lower:
        normalized = normalized.lower()
    return normalized.strip()


# TODO: extend text cleaning with configurable punctuation and multilingual normalization rules.
