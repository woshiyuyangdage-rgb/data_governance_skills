"""Tests for shared timestamp helpers."""

from datetime import date, datetime
import re

from app.core.utils.time_utils import utc_now_compact, utc_now_seconds, utc_today


def test_utc_now_seconds_keeps_legacy_iso_shape() -> None:
    timestamp = utc_now_seconds()

    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is None
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", timestamp)


def test_utc_now_compact_keeps_filename_safe_shape() -> None:
    timestamp = utc_now_compact()

    assert re.fullmatch(r"\d{8}_\d{6}", timestamp)


def test_utc_today_returns_date() -> None:
    assert isinstance(utc_today(), date)
