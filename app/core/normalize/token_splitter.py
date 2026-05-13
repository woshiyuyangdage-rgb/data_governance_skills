"""Token splitting helpers for metadata normalization."""

import re

from app.core.normalize.text_cleaner import clean_text

CAMEL_BOUNDARY_PATTERN = re.compile(r"([a-z0-9])([A-Z])")
PASCAL_BOUNDARY_PATTERN = re.compile(r"([A-Z]+)([A-Z][a-z])")
NON_WORD_PATTERN = re.compile(r"[^A-Za-z0-9_ ]+")


def split_tokens(text: str | None) -> list[str]:
    """Split identifiers or descriptions into reusable tokens."""
    if text is None:
        return []

    normalized = str(text).strip()
    if not normalized:
        return []

    normalized = PASCAL_BOUNDARY_PATTERN.sub(r"\1 \2", normalized)
    normalized = CAMEL_BOUNDARY_PATTERN.sub(r"\1 \2", normalized)
    normalized = normalized.replace("_", " ")
    normalized = NON_WORD_PATTERN.sub(" ", normalized)
    normalized = clean_text(normalized, lower=True)
    return [token for token in normalized.split(" ") if token]


# TODO: extend token splitting with number-unit grouping and multilingual token heuristics.
