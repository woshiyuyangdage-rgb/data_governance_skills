"""Timezone-aware timestamp helpers for local governance artifacts."""

from __future__ import annotations

from datetime import UTC, date, datetime


def utc_now_seconds() -> str:
    """Return a UTC ISO timestamp without timezone suffix, matching legacy output."""
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def utc_now_compact() -> str:
    """Return a compact UTC timestamp for local file names."""
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def utc_today() -> date:
    """Return today's UTC calendar date."""
    return datetime.now(UTC).date()
