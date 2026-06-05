"""Local backup helpers for learning-memory files."""

from __future__ import annotations

import json
import shutil
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
