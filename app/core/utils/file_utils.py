"""File helpers for local MVP upload and output workflows."""

import re
from pathlib import Path
from uuid import uuid4


def ensure_directory(path: str | Path) -> None:
    """Create a directory if it does not already exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_extension(path: str | Path) -> str:
    """Return a lower-cased file extension."""
    return Path(path).suffix.lower()


def sanitize_filename(name: str) -> str:
    """Normalize filenames to a safe local form."""
    candidate = Path(name).name.strip()
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate)
    candidate = candidate.strip("._")
    return candidate or "uploaded_file"


def save_uploaded_file(uploaded_file: object, target_dir: str | Path) -> str:
    """Persist a Streamlit uploaded file object to a local directory."""
    ensure_directory(target_dir)

    file_name = sanitize_filename(getattr(uploaded_file, "name", "uploaded_file"))
    stem = Path(file_name).stem or "uploaded_file"
    suffix = Path(file_name).suffix.lower()
    destination = Path(target_dir) / f"{stem}_{uuid4().hex[:8]}{suffix}"

    buffer = uploaded_file.getbuffer()
    destination.write_bytes(bytes(buffer))
    return str(destination)

