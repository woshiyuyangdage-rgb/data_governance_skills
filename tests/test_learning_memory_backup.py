"""Tests for learning-memory backup helpers."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.learning.learning_memory_backup import (
    LearningMemoryFileSpec,
    create_learning_memory_backup,
    list_learning_memory_backups,
    restore_learning_memory_backup,
    validate_learning_memory_backup,
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
    assert len(manifest["files"][0]["sha256"]) == 64
    assert Path(manifest["files"][0]["backup_path"]).read_text(encoding="utf-8") == (
        mapping_memory.read_text(encoding="utf-8")
    )
    assert backups[0]["backup_id"] == result["backup_id"]
    assert backups[0]["manifest_path"] == str(manifest_path)


def test_learning_memory_backup_validation_reports_restorable_and_skipped_files(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    stg_memory = source_dir / "stg_field_memory.csv"
    stg_memory.write_text(
        "field_key,final_stg_field_name\ncust_id,customer_id\n",
        encoding="utf-8",
    )
    missing_memory = source_dir / "missing.csv"
    backup_root = tmp_path / "backups"
    backup = create_learning_memory_backup(
        backup_root=backup_root,
        file_specs=(
            LearningMemoryFileSpec(
                memory_type="stg_standardization",
                source_path=stg_memory,
                backup_subdir="stg_standardization",
            ),
            LearningMemoryFileSpec(
                memory_type="metadata_completion",
                source_path=missing_memory,
                backup_subdir="metadata_completion",
            ),
        ),
    )

    validation = validate_learning_memory_backup(
        str(backup["backup_id"]),
        backup_root=backup_root,
        file_specs=(
            LearningMemoryFileSpec(
                memory_type="stg_standardization",
                source_path=stg_memory,
                backup_subdir="stg_standardization",
            ),
            LearningMemoryFileSpec(
                memory_type="metadata_completion",
                source_path=missing_memory,
                backup_subdir="metadata_completion",
            ),
        ),
    )

    assert validation["is_valid"] is True
    assert validation["restorable_file_count"] == 1
    assert validation["issue_count"] == 0
    assert validation["skipped_file_count"] == 1
    assert validation["skipped_files"][0]["reason"] == "missing_in_backup"


def test_learning_memory_backup_validation_detects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    mapping_memory = source_dir / "standard_mapping_memory.csv"
    mapping_memory.write_text(
        "field_key,standard_code\ncust_id,customer_id\n",
        encoding="utf-8",
    )
    backup_root = tmp_path / "backups"
    file_specs = (
        LearningMemoryFileSpec(
            memory_type="standard_mapping",
            source_path=mapping_memory,
            backup_subdir="standard_mapping",
        ),
    )
    backup = create_learning_memory_backup(
        backup_root=backup_root,
        file_specs=file_specs,
    )
    manifest = json.loads(Path(str(backup["manifest_path"])).read_text(encoding="utf-8"))
    Path(manifest["files"][0]["backup_path"]).write_text(
        "field_key,standard_code\ncust_id,corrupted\n",
        encoding="utf-8",
    )

    validation = validate_learning_memory_backup(
        str(backup["backup_id"]),
        backup_root=backup_root,
        file_specs=file_specs,
    )

    assert validation["is_valid"] is False
    assert validation["restorable_file_count"] == 0
    assert validation["issues"][0]["reason"] == "checksum_mismatch"


def test_learning_memory_backup_validation_reports_restore_actions(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    unchanged_memory = source_dir / "unchanged.csv"
    changed_memory = source_dir / "changed.csv"
    new_memory = source_dir / "new.csv"
    unchanged_memory.write_text("field_key,value\ncust_id,customer_id\n", encoding="utf-8")
    changed_memory.write_text("field_key,value\nacct_id,account_id\n", encoding="utf-8")
    new_memory.write_text("field_key,value\ncontract_id,contract_id\n", encoding="utf-8")
    backup_root = tmp_path / "backups"
    file_specs = (
        LearningMemoryFileSpec(
            memory_type="standard_mapping",
            source_path=unchanged_memory,
            backup_subdir="standard_mapping",
        ),
        LearningMemoryFileSpec(
            memory_type="standard_mapping",
            source_path=changed_memory,
            backup_subdir="standard_mapping",
        ),
        LearningMemoryFileSpec(
            memory_type="standard_mapping",
            source_path=new_memory,
            backup_subdir="standard_mapping",
        ),
    )
    backup = create_learning_memory_backup(
        backup_root=backup_root,
        file_specs=file_specs,
    )
    changed_memory.write_text("field_key,value\nacct_id,changed\n", encoding="utf-8")
    new_memory.unlink()

    validation = validate_learning_memory_backup(
        str(backup["backup_id"]),
        backup_root=backup_root,
        file_specs=file_specs,
    )
    actions = {
        Path(str(item["source_path"])).name: item["restore_action"]
        for item in validation["restorable_files"]
    }

    assert actions["unchanged.csv"] == "no_change"
    assert actions["changed.csv"] == "overwrite"
    assert actions["new.csv"] == "create"


def test_learning_memory_backup_restores_files_and_creates_pre_restore_backup(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    field_memory = source_dir / "field_completion_memory.csv"
    field_memory.write_text(
        "field_key,field_name_cn\ncustomer_id,Customer ID\n",
        encoding="utf-8",
    )
    backup_root = tmp_path / "backups"
    file_specs = (
        LearningMemoryFileSpec(
            memory_type="metadata_completion",
            source_path=field_memory,
            backup_subdir="metadata_completion",
        ),
    )
    backup = create_learning_memory_backup(
        backup_root=backup_root,
        file_specs=file_specs,
    )
    field_memory.write_text(
        "field_key,field_name_cn\ncustomer_id,Broken value\n",
        encoding="utf-8",
    )

    result = restore_learning_memory_backup(
        str(backup["backup_id"]),
        backup_root=backup_root,
        file_specs=file_specs,
    )

    assert result["restored_file_count"] == 1
    assert result["skipped_file_count"] == 0
    assert result["pre_restore_backup"]["backed_up_file_count"] == 1
    assert field_memory.read_text(encoding="utf-8") == (
        "field_key,field_name_cn\ncustomer_id,Customer ID\n"
    )
