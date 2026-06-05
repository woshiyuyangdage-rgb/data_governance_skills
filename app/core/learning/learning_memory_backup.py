"""Local backup helpers for learning-memory files."""

from __future__ import annotations

import json
import shutil
from hashlib import sha256
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.parser.metadata_learning import FIELD_MEMORY_PATH, TABLE_MEMORY_PATH
from app.core.review.quality_override_store import QUALITY_RULE_OVERRIDES_PATH
from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    STANDARD_MAPPING_MEMORY_PATH,
)
from app.core.skills.stg_standardization_skill.stg_learning import (
    STG_FIELD_MEMORY_PATH,
)
from app.core.utils.file_utils import ensure_directory
from app.core.utils.time_utils import utc_now_compact, utc_now_seconds

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEARNING_BACKUP_DIR = PROJECT_ROOT / "app" / "data" / "learning_backups"


@dataclass(frozen=True)
class LearningMemoryFileSpec:
    """One source file included in learning-memory backups."""

    memory_type: str
    source_path: Path
    backup_subdir: str


@dataclass(frozen=True)
class LearningMemoryBackupFile:
    """One file copy result inside a learning-memory backup."""

    memory_type: str
    source_path: str
    backup_path: str | None
    exists: bool
    size_bytes: int = 0
    sha256: str | None = None


DEFAULT_LEARNING_MEMORY_FILE_SPECS: tuple[LearningMemoryFileSpec, ...] = (
    LearningMemoryFileSpec(
        memory_type="metadata_completion",
        source_path=FIELD_MEMORY_PATH,
        backup_subdir="metadata_completion",
    ),
    LearningMemoryFileSpec(
        memory_type="metadata_completion",
        source_path=TABLE_MEMORY_PATH,
        backup_subdir="metadata_completion",
    ),
    LearningMemoryFileSpec(
        memory_type="standard_mapping",
        source_path=STANDARD_MAPPING_MEMORY_PATH,
        backup_subdir="standard_mapping",
    ),
    LearningMemoryFileSpec(
        memory_type="stg_standardization",
        source_path=STG_FIELD_MEMORY_PATH,
        backup_subdir="stg_standardization",
    ),
    LearningMemoryFileSpec(
        memory_type="quality_rules",
        source_path=QUALITY_RULE_OVERRIDES_PATH,
        backup_subdir="quality_rules",
    ),
)


def _unique_backup_dir(backup_root: Path) -> Path:
    timestamp = utc_now_compact()
    candidate = backup_root / f"learning_memory_{timestamp}"
    if not candidate.exists():
        return candidate
    suffix = 1
    while True:
        candidate = backup_root / f"learning_memory_{timestamp}_{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def _resolve_backup_package_dir(
    backup_id: str,
    backup_root: str | Path | None = None,
) -> Path:
    root = Path(backup_root or LEARNING_BACKUP_DIR).resolve()
    candidate = (root / str(backup_id or "").strip()).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("backup_id must resolve inside the learning backup directory.")
    if not candidate.exists() or not candidate.is_dir():
        raise FileNotFoundError(f"Learning-memory backup does not exist: {backup_id}")
    return candidate


def _allowed_restore_targets(
    file_specs: tuple[LearningMemoryFileSpec, ...],
) -> dict[str, LearningMemoryFileSpec]:
    return {str(Path(spec.source_path).resolve()): spec for spec in file_specs}


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_learning_memory_backup(
    *,
    backup_root: str | Path | None = None,
    file_specs: tuple[LearningMemoryFileSpec, ...] = DEFAULT_LEARNING_MEMORY_FILE_SPECS,
) -> dict[str, object]:
    """Create a local timestamped backup package for learning-memory files."""
    root = Path(backup_root or LEARNING_BACKUP_DIR)
    ensure_directory(root)
    package_dir = _unique_backup_dir(root)
    ensure_directory(package_dir)

    copied_files: list[LearningMemoryBackupFile] = []
    for spec in file_specs:
        source_path = Path(spec.source_path)
        if not source_path.exists():
            copied_files.append(
                LearningMemoryBackupFile(
                    memory_type=spec.memory_type,
                    source_path=str(source_path),
                    backup_path=None,
                    exists=False,
                )
            )
            continue

        target_dir = package_dir / spec.backup_subdir
        ensure_directory(target_dir)
        backup_path = target_dir / source_path.name
        shutil.copy2(source_path, backup_path)
        copied_files.append(
            LearningMemoryBackupFile(
                memory_type=spec.memory_type,
                source_path=str(source_path),
                backup_path=str(backup_path),
                exists=True,
                size_bytes=backup_path.stat().st_size,
                sha256=_file_sha256(backup_path),
            )
        )

    existing_files = [file for file in copied_files if file.exists]
    missing_files = [file for file in copied_files if not file.exists]
    manifest = {
        "backup_id": package_dir.name,
        "created_at": utc_now_seconds(),
        "backup_dir": str(package_dir),
        "backed_up_file_count": len(existing_files),
        "missing_file_count": len(missing_files),
        "files": [asdict(file) for file in copied_files],
        "summary": (
            f"Backed up {len(existing_files)} learning-memory files; "
            f"{len(missing_files)} source files were missing."
        ),
    }
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        **manifest,
        "manifest_path": str(manifest_path),
    }


def list_learning_memory_backups(
    backup_root: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return learning-memory backup manifests, newest first."""
    root = Path(backup_root or LEARNING_BACKUP_DIR)
    if not root.exists():
        return []

    backups: list[dict[str, object]] = []
    for package_dir in sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        manifest_path = package_dir / "manifest.json"
        if not manifest_path.exists():
            backups.append(
                {
                    "backup_id": package_dir.name,
                    "backup_dir": str(package_dir),
                    "manifest_path": None,
                    "backed_up_file_count": None,
                    "missing_file_count": None,
                }
            )
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {
                "backup_id": package_dir.name,
                "backup_dir": str(package_dir),
                "backed_up_file_count": None,
                "missing_file_count": None,
            }
        payload["manifest_path"] = str(manifest_path)
        backups.append(payload)
    return backups


def validate_learning_memory_backup(
    backup_id: str,
    *,
    backup_root: str | Path | None = None,
    file_specs: tuple[LearningMemoryFileSpec, ...] = DEFAULT_LEARNING_MEMORY_FILE_SPECS,
) -> dict[str, object]:
    """Validate a learning-memory backup package before restore."""
    package_dir = _resolve_backup_package_dir(backup_id, backup_root)
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return {
            "backup_id": package_dir.name,
            "manifest_path": str(manifest_path),
            "is_valid": False,
            "restorable_file_count": 0,
            "issue_count": 1,
            "issues": [{"reason": "manifest_missing", "manifest_path": str(manifest_path)}],
            "restorable_files": [],
        }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "backup_id": package_dir.name,
            "manifest_path": str(manifest_path),
            "is_valid": False,
            "restorable_file_count": 0,
            "issue_count": 1,
            "issues": [{"reason": "manifest_invalid_json", "detail": str(exc)}],
            "restorable_files": [],
        }

    files = manifest.get("files", [])
    if not isinstance(files, list):
        return {
            "backup_id": package_dir.name,
            "manifest_path": str(manifest_path),
            "is_valid": False,
            "restorable_file_count": 0,
            "issue_count": 1,
            "issues": [{"reason": "manifest_files_not_list"}],
            "restorable_files": [],
        }

    allowed_targets = _allowed_restore_targets(file_specs)
    issues: list[dict[str, object]] = []
    skipped_files: list[dict[str, object]] = []
    restorable_files: list[dict[str, object]] = []
    package_root = package_dir.resolve()
    for item in files:
        if not isinstance(item, dict):
            issues.append({"reason": "invalid_manifest_item"})
            continue
        if not item.get("exists"):
            skipped_files.append(
                {
                    "source_path": item.get("source_path"),
                    "backup_path": item.get("backup_path"),
                    "reason": "missing_in_backup",
                }
            )
            continue

        source_path_text = str(item.get("source_path") or "")
        target_spec = allowed_targets.get(str(Path(source_path_text).resolve()))
        if target_spec is None:
            issues.append(
                {
                    "source_path": source_path_text,
                    "backup_path": item.get("backup_path"),
                    "reason": "target_not_allowed",
                }
            )
            continue

        backup_path = Path(str(item.get("backup_path") or "")).resolve()
        if package_root != backup_path and package_root not in backup_path.parents:
            issues.append(
                {
                    "source_path": source_path_text,
                    "backup_path": str(backup_path),
                    "reason": "backup_path_outside_package",
                }
            )
            continue
        if not backup_path.exists() or not backup_path.is_file():
            issues.append(
                {
                    "source_path": source_path_text,
                    "backup_path": str(backup_path),
                    "reason": "backup_file_missing",
                }
            )
            continue
        expected_sha256 = item.get("sha256")
        actual_sha256 = _file_sha256(backup_path)
        if expected_sha256 and str(expected_sha256) != actual_sha256:
            issues.append(
                {
                    "source_path": source_path_text,
                    "backup_path": str(backup_path),
                    "reason": "checksum_mismatch",
                    "expected_sha256": str(expected_sha256),
                    "actual_sha256": actual_sha256,
                }
            )
            continue

        target_path = Path(target_spec.source_path)
        target_exists = target_path.exists()
        target_size_bytes = target_path.stat().st_size if target_exists else 0
        target_sha256 = _file_sha256(target_path) if target_exists else None
        restore_action = (
            "create"
            if not target_exists
            else ("no_change" if target_sha256 == actual_sha256 else "overwrite")
        )
        restorable_files.append(
            {
                "memory_type": target_spec.memory_type,
                "source_path": str(target_path),
                "backup_path": str(backup_path),
                "size_bytes": backup_path.stat().st_size,
                "sha256": actual_sha256,
                "target_exists": target_exists,
                "target_size_bytes": target_size_bytes,
                "target_sha256": target_sha256,
                "restore_action": restore_action,
            }
        )

    return {
        "backup_id": package_dir.name,
        "manifest_path": str(manifest_path),
        "is_valid": not issues and bool(restorable_files),
        "restorable_file_count": len(restorable_files),
        "issue_count": len(issues),
        "skipped_file_count": len(skipped_files),
        "issues": issues,
        "skipped_files": skipped_files,
        "restorable_files": restorable_files,
        "summary": (
            f"Backup {package_dir.name} has {len(restorable_files)} restorable files "
            f"and {len(issues)} validation issues."
        ),
    }


def restore_learning_memory_backup(
    backup_id: str,
    *,
    backup_root: str | Path | None = None,
    file_specs: tuple[LearningMemoryFileSpec, ...] = DEFAULT_LEARNING_MEMORY_FILE_SPECS,
    create_pre_restore_backup: bool = True,
) -> dict[str, object]:
    """Restore learning-memory files from a timestamped backup package."""
    package_dir = _resolve_backup_package_dir(backup_id, backup_root)
    manifest_path = package_dir / "manifest.json"
    validation = validate_learning_memory_backup(
        backup_id,
        backup_root=backup_root,
        file_specs=file_specs,
    )
    if not validation["restorable_files"]:
        raise ValueError("Backup contains no restorable learning-memory files.")

    root = Path(backup_root or LEARNING_BACKUP_DIR)
    pre_restore_backup = (
        create_learning_memory_backup(backup_root=root, file_specs=file_specs)
        if create_pre_restore_backup
        else None
    )
    restored_files: list[dict[str, object]] = []
    for item in validation["restorable_files"]:
        backup_path = Path(str(item["backup_path"]))
        target_path = Path(str(item["source_path"]))
        ensure_directory(target_path.parent)
        shutil.copy2(backup_path, target_path)
        restored_files.append(
            {
                "memory_type": item["memory_type"],
                "source_path": str(target_path),
                "backup_path": str(backup_path),
                "size_bytes": target_path.stat().st_size,
            }
        )

    return {
        "backup_id": package_dir.name,
        "manifest_path": str(manifest_path),
        "restored_file_count": len(restored_files),
        "skipped_file_count": int(validation["issue_count"])
        + int(validation.get("skipped_file_count", 0)),
        "restored_files": restored_files,
        "skipped_files": [
            *list(validation.get("skipped_files", [])),
            *list(validation["issues"]),
        ],
        "validation": validation,
        "pre_restore_backup": pre_restore_backup,
        "summary": (
            f"Restored {len(restored_files)} learning-memory files from "
            f"{package_dir.name}; skipped "
            f"{int(validation['issue_count']) + int(validation.get('skipped_file_count', 0))} files."
        ),
    }
