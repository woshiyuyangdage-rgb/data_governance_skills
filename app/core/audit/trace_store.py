"""Local execution trace storage for tool-layer audit records."""

from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from app.core.models.execution_trace import ExecutionTrace
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRACE_DIR = PROJECT_ROOT / "app" / "data" / "audit" / "execution_traces"


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _trace_path(trace_id: str) -> Path:
    return TRACE_DIR / f"{trace_id}.json"


def trace_to_dict(trace: ExecutionTrace) -> dict[str, object]:
    """Convert one trace model into a JSON-serializable dictionary."""
    return trace.model_dump()


def build_trace_summary(
    tool_name: str,
    status: str = "started",
    session_id: str | None = None,
    profile_name: str | None = None,
    asset_name: str | None = None,
    operation: str | None = None,
    validation_status: str | None = None,
    raw_text: str | None = None,
    input_summary: dict[str, object] | None = None,
) -> ExecutionTrace:
    """Create a new execution trace with a generated id."""
    return ExecutionTrace(
        trace_id=uuid4().hex,
        session_id=session_id,
        tool_name=tool_name,
        profile_name=profile_name,
        asset_name=asset_name,
        operation=operation,
        validation_status=validation_status,
        raw_text=raw_text,
        input_summary=input_summary or {},
        status=status,
        started_at=_utc_now(),
    )


def save_trace(trace: ExecutionTrace) -> ExecutionTrace:
    """Persist one execution trace as a local JSON file."""
    ensure_directory(TRACE_DIR)
    if not trace.trace_id:
        trace.trace_id = uuid4().hex
    if not trace.started_at:
        trace.started_at = _utc_now()
    if not trace.finished_at and trace.status != "started":
        trace.finished_at = _utc_now()

    path = _trace_path(trace.trace_id)
    path.write_text(
        json.dumps(trace_to_dict(trace), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return trace


def get_trace(trace_id: str) -> ExecutionTrace | None:
    """Return one persisted trace by id if it exists."""
    path = _trace_path(trace_id)
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExecutionTrace.model_validate(payload)


def list_recent_traces(limit: int = 20) -> list[ExecutionTrace]:
    """Return recent traces sorted by file modification time."""
    if not TRACE_DIR.exists():
        return []

    trace_files = sorted(
        TRACE_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    traces: list[ExecutionTrace] = []
    for path in trace_files[: max(0, int(limit))]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        traces.append(ExecutionTrace.model_validate(payload))
    return traces
