"""Lightweight in-memory session store for the agent shell."""

import json
from pathlib import Path
from uuid import uuid4

from app.core.agent.agent_loader import load_agent_shell_config
from app.core.models.agent_session import AgentSession
from app.core.models.execution_plan import ExecutionPlan
from app.core.utils.file_utils import ensure_directory
from app.core.utils.time_utils import utc_now_seconds

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SESSION_SNAPSHOT_DIR = PROJECT_ROOT / "outputs" / "agent_sessions"
_SESSION_STORE: dict[str, AgentSession] = {}


def _utc_now() -> str:
    return utc_now_seconds()


def _max_recent_items() -> int:
    config = load_agent_shell_config()
    session_policy = config.get("session_policy", {})
    return int(session_policy.get("max_recent_plans", 10))


def _append_recent_unique(values: list[str], new_value: str) -> list[str]:
    normalized_value = str(new_value).strip()
    if not normalized_value:
        return values[-_max_recent_items() :]

    recent_values = [str(item) for item in values if str(item).strip() != normalized_value]
    recent_values.append(normalized_value)
    return recent_values[-_max_recent_items() :]


def _snapshot_session(session: AgentSession) -> None:
    ensure_directory(SESSION_SNAPSHOT_DIR)
    snapshot_path = SESSION_SNAPSHOT_DIR / f"{session.session_id}.json"
    snapshot_path.write_text(
        json.dumps(session.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_session_snapshots() -> list[Path]:
    """Return saved session snapshot files, newest first."""
    if not SESSION_SNAPSHOT_DIR.exists():
        return []
    return sorted(
        [
            path
            for path in SESSION_SNAPSHOT_DIR.iterdir()
            if path.is_file() and path.suffix.lower() == ".json"
        ],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def load_session_from_snapshot(snapshot_path: str | Path) -> AgentSession | None:
    """Load one saved session snapshot into memory."""
    resolved_path = Path(snapshot_path)
    if not resolved_path.exists() or not resolved_path.is_file():
        return None

    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        session = AgentSession.model_validate(payload)
    except Exception:
        return None

    _SESSION_STORE[session.session_id] = session
    return session


def load_latest_session_snapshot() -> AgentSession | None:
    """Load the most recent session snapshot into memory."""
    for snapshot_path in list_session_snapshots():
        session = load_session_from_snapshot(snapshot_path)
        if session is not None:
            return session
    return None


def create_session(session_id: str | None = None) -> AgentSession:
    """Create a new local agent shell session."""
    resolved_session_id = session_id or uuid4().hex
    session = AgentSession(session_id=resolved_session_id, created_at=_utc_now())
    _SESSION_STORE[resolved_session_id] = session
    _snapshot_session(session)
    return session


def get_session(session_id: str) -> AgentSession | None:
    """Return a stored session if it exists."""
    return _SESSION_STORE.get(session_id)


def save_session(session: AgentSession) -> AgentSession:
    """Save or replace one session in the local store."""
    _SESSION_STORE[session.session_id] = session
    _snapshot_session(session)
    return session


def append_plan_to_session(session_id: str, plan: ExecutionPlan) -> AgentSession:
    """Append one execution plan to a session, creating it if needed."""
    session = get_session(session_id) or create_session(session_id)
    recent_plans = list(session.recent_plans)
    recent_plans.append(plan)
    session.recent_plans = recent_plans[-_max_recent_items() :]
    return save_session(session)


def append_request_to_session(session_id: str, raw_text: str) -> AgentSession:
    """Append one raw request string to a session, creating it if needed."""
    session = get_session(session_id) or create_session(session_id)
    recent_requests = list(session.recent_requests)
    recent_requests.append(raw_text)
    session.recent_requests = recent_requests[-_max_recent_items() :]
    return save_session(session)


def append_trace_to_session(session_id: str, trace_id: str) -> AgentSession:
    """Append one trace id to a session, creating it if needed."""
    session = get_session(session_id) or create_session(session_id)
    session.last_trace_id = str(trace_id).strip() or None
    session.recent_trace_ids = _append_recent_unique(
        list(session.recent_trace_ids),
        trace_id,
    )
    return save_session(session)


def set_last_uploaded_file(session_id: str, file_path: str) -> AgentSession:
    """Persist the most recent uploaded file path for one session."""
    session = get_session(session_id) or create_session(session_id)
    session.last_uploaded_file_path = str(file_path).strip() or None
    session.recent_uploaded_files = _append_recent_unique(
        list(session.recent_uploaded_files),
        file_path,
    )
    return save_session(session)


def set_last_exported_files(
    session_id: str,
    exported_files: dict[str, str],
) -> AgentSession:
    """Persist the latest exported report files for one session."""
    session = get_session(session_id) or create_session(session_id)
    session.last_exported_files = {
        str(key): str(value)
        for key, value in exported_files.items()
        if str(value).strip()
    }
    return save_session(session)


def set_last_task_context(
    session_id: str,
    task_request=None,
    task_response=None,
) -> AgentSession:
    """Persist the latest task request and response for one session."""
    session = get_session(session_id) or create_session(session_id)
    if task_request is not None:
        session.last_task_request = task_request
    if task_response is not None:
        session.last_task_response = task_response
    return save_session(session)


def set_last_tool_response(
    session_id: str,
    tool_response,
) -> AgentSession:
    """Persist the latest tool-call response for one session."""
    session = get_session(session_id) or create_session(session_id)
    session.last_tool_response = tool_response
    return save_session(session)


def get_recent_file_candidates(session_id: str) -> list[str]:
    """Return recent unique file candidates for one session."""
    session = get_session(session_id)
    if session is None:
        return []

    ordered_candidates: list[str] = []
    seen: set[str] = set()
    candidate_pool = list(reversed(session.recent_uploaded_files))
    if session.last_uploaded_file_path:
        candidate_pool.append(session.last_uploaded_file_path)
    if session.last_task_request is not None and session.last_task_request.file_path:
        candidate_pool.append(session.last_task_request.file_path)

    for candidate in candidate_pool:
        normalized = str(candidate).strip()
        if normalized and normalized not in seen:
            ordered_candidates.append(normalized)
            seen.add(normalized)

    return ordered_candidates


def clear_session_store() -> None:
    """Clear in-memory session state for tests or local resets."""
    _SESSION_STORE.clear()


# TODO: replace the in-memory store with durable local or shared storage if the shell ever grows beyond single-user local usage.
