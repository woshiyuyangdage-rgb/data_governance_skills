"""Tests for learning-memory backup helpers."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.learning.learning_memory_backup import (
    LearningMemoryFileSpec,
    create_learning_memory_backup,
    list_learning_memory_backups,
)


def test_learning_memory_backup_copies_existing_files_and_records_missing(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    mapping_memory = source_dir / "standard_mapping_memory.csv"
    mapping_memory.write_text(
        "table_key,field_key,standard_code\ncustomer,cust_id,customer_id\n",
        encoding="utf-8",
    )
    missing_memory = source_dir / "missing.csv"
    backup_root = tmp_path / "backups"

    result = create_learning_memory_backup(
        backup_root=backup_root,
        file_specs=(
            LearningMemoryFileSpec(
                memory_type="standard_mapping",
                source_path=mapping_memory,
                backup_subdir="standard_mapping",
            ),
            LearningMemoryFileSpec(
                memory_type="metadata_completion",
                source_path=missing_memory,
                backup_subdir="metadata_completion",
            ),
        ),
    )

    manifest_path = Path(str(result["manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backups = list_learning_memory_backups(backup_root)

    assert result["backed_up_file_count"] == 1
    assert result["missing_file_count"] == 1
    assert manifest["files"][0]["exists"] is True
    assert manifest["files"][1]["exists"] is False
    assert Path(manifest["files"][0]["backup_path"]).read_text(encoding="utf-8") == (
        mapping_memory.read_text(encoding="utf-8")
    )
    assert backups[0]["backup_id"] == result["backup_id"]
    assert backups[0]["manifest_path"] == str(manifest_path)
