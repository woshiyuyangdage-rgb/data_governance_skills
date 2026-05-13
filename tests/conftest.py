"""Test fixtures for Windows-safe local temporary paths."""

from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_path(request) -> Path:
    """Provide a writable test temp path without relying on the system temp root."""
    safe_name = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_"
        for character in request.node.name
    )
    path = PROJECT_ROOT / "outputs" / "pytest_runtime" / f"{safe_name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path

