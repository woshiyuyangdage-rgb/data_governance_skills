"""Shared helpers for control-plane asset validators."""

from typing import Any


def _records_from_content(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        return [record if isinstance(record, dict) else {"value": record} for record in content]
    raise ValueError("CSV content must be a list of row dictionaries.")
