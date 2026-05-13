"""Local JSON snapshot store for batch incremental rerun."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.core.models.object_fingerprint import ObjectFingerprint
from app.core.utils.file_utils import ensure_directory, sanitize_filename

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = PROJECT_ROOT / "app" / "data" / "batch_snapshots"


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _batch_dir(batch_name: str) -> Path:
    return SNAPSHOT_DIR / sanitize_filename(batch_name)


def save_batch_snapshot(
    batch_name: str,
    fingerprints: list[ObjectFingerprint],
    metadata: dict[str, Any] | None = None,
) -> str:
    """Persist one batch fingerprint snapshot as JSON."""
    ensure_directory(_batch_dir(batch_name))
    generated_at = _utc_now()
    path = _batch_dir(batch_name) / f"{generated_at.replace(':', '')}.json"
    payload = {
        "batch_name": batch_name,
        "generated_at": generated_at,
        "metadata": metadata or {},
        "fingerprints": [item.model_dump() for item in fingerprints],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def list_batch_snapshots(batch_name: str) -> list[dict[str, Any]]:
    """List snapshots for one batch, newest first."""
    directory = _batch_dir(batch_name)
    if not directory.exists():
        return []
    snapshots = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append(
            {
                "path": str(path),
                "batch_name": payload.get("batch_name", batch_name),
                "generated_at": payload.get("generated_at"),
                "metadata": payload.get("metadata", {}),
                "fingerprint_count": len(payload.get("fingerprints", [])),
            }
        )
    return snapshots


def load_latest_batch_snapshot(batch_name: str) -> dict[str, Any] | None:
    """Load the newest snapshot payload for one batch."""
    snapshots = list_batch_snapshots(batch_name)
    if not snapshots:
        return None
    path = Path(str(snapshots[0]["path"]))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fingerprints"] = [
        ObjectFingerprint.model_validate(item)
        for item in payload.get("fingerprints", [])
    ]
    payload["path"] = str(path)
    return payload

