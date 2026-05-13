"""Tests for file utility helpers."""

from pathlib import Path

from app.core.utils.file_utils import (
    ensure_directory,
    get_file_extension,
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
