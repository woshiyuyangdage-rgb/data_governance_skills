"""Tests for the lightweight agent shell service."""

from pathlib import Path

from app.core.agent.agent_shell_service import AgentShellService
from app.core.agent import session_store

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def _patch_session_snapshot_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()


def test_agent_shell_interpret_to_plan_returns_execution_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()

    result = service.interpret_to_plan(
        text="Help me inspect this file",
        file_path=str(SAMPLE_METADATA_PATH),
    )

    assert result.execution_plan.profile_name == "metadata_diagnosis_only"
    assert result.execution_plan.validation_passed is True
    assert result.task_response is None
    assert result.session_id is not None


def test_agent_shell_can_autofill_file_from_current_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))

    result = service.interpret_to_plan(
        text="Help me inspect this file",
        session_id=session.session_id,
    )

    assert result.execution_plan.validation_passed is True
    assert result.task_request.file_path == str(SAMPLE_METADATA_PATH)
    assert result.resolution_applied is True
    assert result.resolved_context is not None
    assert result.resolved_context.resolved_file_path == str(SAMPLE_METADATA_PATH)


def test_agent_shell_requires_confirmation_before_running_stg(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()

    result = service.confirm_and_run(
        text="Generate STG structure suggestions",
        file_path=str(SAMPLE_METADATA_PATH),
    )

    assert result.status == "preview_requires_confirmation"
    assert result.execution_plan.requires_confirmation is True
    assert result.task_response is None


def test_agent_shell_force_run_executes_when_confirmation_is_required(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()

    result = service.confirm_and_run(
        text="Generate STG structure suggestions",
        file_path=str(SAMPLE_METADATA_PATH),
        force_run=True,
    )

    assert result.status == "executed_successfully"
    assert result.task_response is not None
    assert result.task_response.status == "success"


def test_agent_shell_blocks_execution_when_session_file_context_is_ambiguous(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))
    session_store.set_last_task_context(
        session.session_id,
        task_request=service.interpreter.build_task_request(
            service.interpreter.interpret("Help me inspect this file"),
            file_path="other.csv",
        ),
    )

    result = service.confirm_and_run(
        text="Run diagnosis",
        session_id=session.session_id,
    )

    assert result.status == "validation_failed"
    assert result.task_response is None
    assert result.resolved_context is not None
    assert result.resolved_context.ambiguity_detected is True


def test_agent_shell_validation_failed_blocks_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()

    result = service.confirm_and_run(text="Help me inspect this file")

    assert result.status == "validation_failed"
    assert result.task_response is None
    assert result.execution_plan.validation_passed is False


def test_agent_shell_execution_updates_last_exported_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))

    result = service.confirm_and_run(
        text="Help me inspect this file and export reports",
        session_id=session.session_id,
        force_run=True,
    )

    assert result.status == "executed_successfully"
    assert result.task_response is not None
    assert result.task_response.exported_files
    loaded = session_store.get_session(session.session_id)
    assert loaded is not None
    assert loaded.last_exported_files == result.task_response.exported_files


def test_agent_shell_session_id_can_be_reused(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_session_snapshot_dir(tmp_path, monkeypatch)
    service = AgentShellService()

    first = service.interpret_to_plan(
        text="Help me inspect this file",
        file_path=str(SAMPLE_METADATA_PATH),
    )
    second = service.interpret_to_plan(
        text="Run standard mapping",
        file_path=str(SAMPLE_METADATA_PATH),
        session_id=first.session_id,
    )

    assert first.session_id == second.session_id
    session = session_store.get_session(first.session_id or "")
    assert session is not None
    assert len(session.recent_requests) == 2
