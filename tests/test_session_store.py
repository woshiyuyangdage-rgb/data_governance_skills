"""Tests for lightweight agent shell session storage."""

from pathlib import Path

from app.core.agent import session_store
from app.core.models.execution_plan import ExecutionPlan
from app.core.models.governance_task_request import GovernanceTaskRequest


def test_session_store_can_create_get_and_save_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    session = session_store.create_session()
    session.recent_requests.append("demo request")
    saved = session_store.save_session(session)
    loaded = session_store.get_session(session.session_id)

    assert saved.session_id == session.session_id
    assert loaded is not None
    assert loaded.recent_requests == ["demo request"]


def test_session_store_can_append_recent_plans(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    session = session_store.create_session()
    plan = ExecutionPlan(
        raw_text="plan request",
        profile_name="metadata_diagnosis_only",
        stages=["diagnosis"],
        file_path="sample.csv",
        validation_passed=True,
    )

    updated = session_store.append_plan_to_session(session.session_id, plan)
    session_store.append_request_to_session(session.session_id, "plan request")

    assert len(updated.recent_plans) == 1
    loaded = session_store.get_session(session.session_id)
    assert loaded is not None
    assert loaded.recent_plans[0].profile_name == "metadata_diagnosis_only"
    assert loaded.recent_requests == ["plan request"]


def test_session_store_can_track_uploaded_files_and_candidates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, "uploaded_a.csv")
    session_store.set_last_uploaded_file(session.session_id, "uploaded_b.csv")
    session_store.set_last_task_context(
        session.session_id,
        task_request=GovernanceTaskRequest(
            file_path="previous.csv",
            profile_name="metadata_diagnosis_only",
        ),
    )

    loaded = session_store.get_session(session.session_id)
    candidates = session_store.get_recent_file_candidates(session.session_id)

    assert loaded is not None
    assert loaded.last_uploaded_file_path == "uploaded_b.csv"
    assert loaded.recent_uploaded_files[-1] == "uploaded_b.csv"
    assert candidates[0] == "uploaded_b.csv"
    assert "previous.csv" in candidates


def test_session_store_can_track_last_exported_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    session = session_store.create_session()
    exported_files = {
        "json": str(tmp_path / "reports" / "sample.json"),
        "excel": str(tmp_path / "reports" / "sample.xlsx"),
    }

    session_store.set_last_exported_files(session.session_id, exported_files)
    loaded = session_store.get_session(session.session_id)

    assert loaded is not None
    assert loaded.last_exported_files == exported_files


def test_session_store_can_track_recent_trace_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    session = session_store.create_session()
    session_store.append_trace_to_session(session.session_id, "trace_a")
    session_store.append_trace_to_session(session.session_id, "trace_b")
    loaded = session_store.get_session(session.session_id)

    assert loaded is not None
    assert loaded.last_trace_id == "trace_b"
    assert loaded.recent_trace_ids[-1] == "trace_b"
