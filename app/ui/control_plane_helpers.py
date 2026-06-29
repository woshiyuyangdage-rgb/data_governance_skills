"""Pure helpers for the Streamlit control-plane page."""

from __future__ import annotations

import hashlib
from difflib import unified_diff


def content_fingerprint(content: str) -> str:
    """Return a stable fingerprint for edited control-plane content."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"{len(content)}::{digest}"


def diff_stats(original_text: str, edited_text: str) -> tuple[int, int]:
    """Return added and removed line counts for a unified diff."""
    diff_lines = list(
        unified_diff(
            original_text.splitlines(),
            edited_text.splitlines(),
            lineterm="",
        )
    )
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return added, removed


def should_warn_baseline_changed(
    previous_fingerprint: str | None,
    current_fingerprint: str,
) -> bool:
    """Return whether a stored editor baseline differs from current disk content."""
    return previous_fingerprint is not None and previous_fingerprint != current_fingerprint


def can_publish_without_save(original_text: str, edited_text: str) -> bool:
    """Return whether the current editor content matches the saved baseline."""
    return original_text == edited_text
