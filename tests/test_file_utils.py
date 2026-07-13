"""Tests for file utility helpers."""

from pathlib import Path

import pytest

from app.core.utils import file_utils
from app.core.utils.file_utils import (
    ALLOWED_LOCAL_ROOTS_ENV,
    LocalPathAccessError,
    configured_allowed_local_roots,
    ensure_directory,
    get_file_extension,
    resolve_allowed_local_path,
    sanitize_filename,
    save_uploaded_file,
)


class DummyUploadedFile:
    """Minimal uploaded file stub for unit tests."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.size = len(content)
        self._content = content

    def getbuffer(self) -> memoryview:
        return memoryview(self._content)


def test_ensure_directory_creates_target_directory(tmp_path: Path) -> None:
    target_dir = tmp_path / "nested" / "uploads"

    ensure_directory(target_dir)

    assert target_dir.exists()
    assert target_dir.is_dir()


def test_get_file_extension_and_sanitize_filename() -> None:
    assert get_file_extension("Sample_Metadata.CSV") == ".csv"
    assert sanitize_filename("sales order?.csv") == "sales_order_.csv"


def test_save_uploaded_file_persists_bytes(tmp_path: Path) -> None:
    uploaded_file = DummyUploadedFile("sales order?.csv", b"table_name\ncustomer_master\n")

    saved_path = save_uploaded_file(uploaded_file, tmp_path)
    saved_file = Path(saved_path)

    assert saved_file.exists()
    assert saved_file.parent == tmp_path
    assert saved_file.read_bytes() == b"table_name\ncustomer_master\n"


def test_resolve_allowed_local_path_accepts_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", project_root)
    monkeypatch.delenv(ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    resolved_path = resolve_allowed_local_path(project_root / "input.csv")

    assert resolved_path == (project_root / "input.csv").resolve(strict=False)


def test_resolve_allowed_local_path_accepts_environment_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", project_root)
    monkeypatch.setenv(ALLOWED_LOCAL_ROOTS_ENV, str(external_root))

    assert external_root.resolve(strict=False) in configured_allowed_local_roots()
    assert resolve_allowed_local_path(external_root / "input.csv") == (
        external_root / "input.csv"
    ).resolve(strict=False)


def test_resolve_allowed_local_path_rejects_outside_roots(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    outside_path = tmp_path / "outside" / "input.csv"

    with pytest.raises(LocalPathAccessError) as exc_info:
        resolve_allowed_local_path(
            outside_path,
            allowed_roots=[allowed_root],
            path_label="file_path",
        )

    assert "outside allowed local roots" in str(exc_info.value)
