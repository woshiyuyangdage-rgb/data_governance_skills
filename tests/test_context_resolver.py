"""Tests for session-aware context resolution."""

from pathlib import Path

from app.core.agent import session_store
from app.core.context.context_resolver import ContextResolver
from app.core.models.governance_task_request import GovernanceTaskRequest


def _patch_session_snapshot_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()


def test_context_resolver_does_not_override_explicit_file_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    resolver = ContextResolver()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, "uploaded.csv")

    result = resolver.resolve(
        raw_text="Help me inspect this file",
        task_request=GovernanceTaskRequest(
            file_path="explicit.csv",
            profile_name="metadata_diagnosis_only",
        ),
        session_id=session.session_id,
    )

    assert result.resolved_task_request.file_path == "explicit.csv"
    assert result.resolution_applied is False
    assert "explicit_file_path" in result.resolved_context.resolved_from


def test_context_resolver_autofills_unique_last_uploaded_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    resolver = ContextResolver()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, "uploaded.csv")

    result = resolver.resolve(
        raw_text="Help me inspect this file",
        task_request=GovernanceTaskRequest(
            file_path=None,
            profile_name="metadata_diagnosis_only",
        ),
        session_id=session.session_id,
    )

    assert result.resolved_task_request.file_path == "uploaded.csv"
    assert result.resolution_applied is True
    assert result.resolved_context.autofilled_parameters["file_path"] == "uploaded.csv"


def test_context_resolver_leaves_missing_file_path_empty_without_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    resolver = ContextResolver()
    session = session_store.create_session()

    result = resolver.resolve(
        raw_text="Help me inspect this file",
        task_request=GovernanceTaskRequest(
            file_path=None,
            profile_name="metadata_diagnosis_only",
        ),
        session_id=session.session_id,
    )

    assert result.resolved_task_request.file_path is None
    assert result.resolution_applied is False
    assert any(
        "No session-based file candidate" in message
        for message in result.resolved_context.messages
    )


def test_context_resolver_marks_ambiguous_candidates_without_autofill(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    resolver = ContextResolver()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, "uploaded.csv")
    session_store.set_last_task_context(
        session.session_id,
        task_request=GovernanceTaskRequest(
            file_path="previous.csv",
            profile_name="metadata_diagnosis_only",
        ),
    )

    result = resolver.resolve(
        raw_text="Run diagnosis",
        task_request=GovernanceTaskRequest(
            file_path=None,
            profile_name="metadata_diagnosis_only",
        ),
        session_id=session.session_id,
    )

    assert result.resolved_task_request.file_path is None
    assert result.resolved_context.ambiguity_detected is True
    assert result.resolution_applied is False


def test_context_resolver_recognizes_chinese_and_english_file_references(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    resolver = ContextResolver()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, "uploaded.csv")
    session_store.set_last_task_context(
        session.session_id,
        task_request=GovernanceTaskRequest(
            file_path="previous.csv",
            profile_name="metadata_diagnosis_only",
        ),
    )

    current_result = resolver.resolve(
        raw_text="\u5e2e\u6211\u68c0\u67e5\u8fd9\u4e2a\u6587\u4ef6\u7684\u95ee\u9898",
        task_request=GovernanceTaskRequest(
            file_path=None,
            profile_name="metadata_diagnosis_only",
        ),
        session_id=session.session_id,
    )
    previous_result = resolver.resolve(
        raw_text="Generate STG suggestions from the last file",
        task_request=GovernanceTaskRequest(
            file_path=None,
            profile_name="diagnosis_mapping_stg",
        ),
        session_id=session.session_id,
    )

    assert current_result.resolved_task_request.file_path == "uploaded.csv"
    assert previous_result.resolved_task_request.file_path == "previous.csv"
