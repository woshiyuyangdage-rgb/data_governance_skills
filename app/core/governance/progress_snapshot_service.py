"""Local progress snapshot service for governance portfolio tracking."""

from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.progress_snapshot import ProgressSnapshot
from app.core.models.readiness_score import ReadinessScore
from app.core.rules.config_loader import get_progress_snapshot_policies_config
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROGRESS_SNAPSHOT_DIR = (
    PROJECT_ROOT / "app" / "data" / "governance_backlog" / "progress_snapshots"
)


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


class ProgressSnapshotService:
    """Build and persist lightweight progress snapshots."""

    def __init__(self, policies: dict[str, object] | None = None) -> None:
        self.policies = policies or get_progress_snapshot_policies_config()

    @staticmethod
    def _avg_readiness_score(readiness_scores: list[ReadinessScore] | None) -> float | None:
        scores = [score.overall_score for score in readiness_scores or []]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 4)

    def build_progress_snapshot(
        self,
        governance_backlog_items: list[GovernanceBacklogItem],
        backlog_sla_statuses: list[BacklogSlaStatus] | None = None,
        readiness_scores: list[ReadinessScore] | None = None,
        notes: str | None = None,
    ) -> ProgressSnapshot:
        """Build one point-in-time progress snapshot."""
        completed_count = sum(
            1 for item in governance_backlog_items if item.status == "completed"
        )
        blocked_count = sum(
            1 for item in governance_backlog_items if item.status == "blocked"
        )
        overdue_count = sum(
            1 for status in backlog_sla_statuses or [] if status.is_overdue
        )
        return ProgressSnapshot(
            snapshot_id=f"snapshot_{uuid4().hex[:12]}",
            generated_at=_utc_now(),
            total_backlog_items=len(governance_backlog_items),
            completed_count=completed_count,
            blocked_count=blocked_count,
            overdue_count=overdue_count,
            avg_readiness_score=self._avg_readiness_score(readiness_scores),
            notes=notes,
        )

    def save_progress_snapshot(self, snapshot: ProgressSnapshot) -> dict[str, object]:
        """Persist one progress snapshot to local JSON storage."""
        ensure_directory(PROGRESS_SNAPSHOT_DIR)
        timestamp = (snapshot.generated_at or _utc_now()).replace(":", "").replace("-", "")
        safe_name = f"{timestamp}_{snapshot.snapshot_id}.json"
        snapshot_path = PROGRESS_SNAPSHOT_DIR / safe_name
        snapshot_path.write_text(
            json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "snapshot_id": snapshot.snapshot_id,
            "path": str(snapshot_path),
            "status": "success",
        }

    def list_progress_snapshots(self) -> list[ProgressSnapshot]:
        """Load saved progress snapshots newest first."""
        if not PROGRESS_SNAPSHOT_DIR.exists():
            return []
        snapshots: list[ProgressSnapshot] = []
        for path in sorted(
            PROGRESS_SNAPSHOT_DIR.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            snapshots.append(ProgressSnapshot.model_validate(payload))
        return snapshots


# TODO: add KPI dashboard and portfolio analytics exports after snapshots stabilize.
