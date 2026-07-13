"""File helpers for local MVP upload and output workflows."""

import os
import re
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_LOCAL_ROOTS_ENV = "DATA_GOVERNANCE_ALLOWED_LOCAL_ROOTS"


class LocalPathAccessError(ValueError):
    """Raised when a local path is outside configured project-safe roots."""


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


def _dedupe_paths(paths: list[Path]) -> tuple[Path, ...]:
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved_path = path.expanduser().resolve(strict=False)
        key = str(resolved_path).casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(resolved_path)
    return tuple(deduped)


def configured_allowed_local_roots() -> tuple[Path, ...]:
    """Return project-safe roots for local file read/write operations."""
    roots = [PROJECT_ROOT, PROJECT_ROOT / "outputs", PROJECT_ROOT / ".pytest_runtime"]
    env_value = os.environ.get(ALLOWED_LOCAL_ROOTS_ENV, "")
    for raw_path in env_value.split(os.pathsep):
        if raw_path.strip():
            roots.append(Path(raw_path.strip()))
    return _dedupe_paths(roots)


def resolve_allowed_local_path(
    path: str | Path,
    *,
    allowed_roots: tuple[Path, ...] | list[Path] | None = None,
    path_label: str = "path",
) -> Path:
    """Resolve a local path and ensure it stays below configured safe roots."""
    resolved_path = Path(path).expanduser().resolve(strict=False)
    roots = (
        _dedupe_paths(list(allowed_roots))
        if allowed_roots is not None
        else configured_allowed_local_roots()
    )
    for root in roots:
        if resolved_path == root or root in resolved_path.parents:
            return resolved_path

    allowed_roots_text = ", ".join(str(root) for root in roots)
    raise LocalPathAccessError(
        f"{path_label} '{path}' is outside allowed local roots: {allowed_roots_text}"
    )


def save_uploaded_file(uploaded_file: object, target_dir: str | Path) -> str:
    """Persist a Streamlit uploaded file object to a local directory."""
    resolved_target_dir = resolve_allowed_local_path(target_dir, path_label="target_dir")
    ensure_directory(resolved_target_dir)

    file_name = sanitize_filename(getattr(uploaded_file, "name", "uploaded_file"))
    stem = Path(file_name).stem or "uploaded_file"
    suffix = Path(file_name).suffix.lower()
    destination = resolved_target_dir / f"{stem}_{uuid4().hex[:8]}{suffix}"

    buffer = uploaded_file.getbuffer()
    destination.write_bytes(bytes(buffer))
    return str(destination)
