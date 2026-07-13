"""Tests for local execution trace storage."""

from pathlib import Path

import pytest

from app.core.audit import trace_store
from app.core.audit.trace_store import (
    build_trace_summary,
    get_trace,
    get_trace_dir,
    list_recent_traces,
    save_trace,
)
from app.core.utils import file_utils
from app.core.utils.file_utils import LocalPathAccessError


def test_trace_store_handles_empty_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")

    traces = list_recent_traces()

    assert traces == []

def test_trace_store_uses_configured_trace_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configured_dir = tmp_path / "configured_traces"
    monkeypatch.setenv(trace_store.TRACE_DIR_ENV, str(configured_dir))

    trace = build_trace_summary(tool_name="configured_trace_dir")
    trace.status = "success"
    saved = save_trace(trace)

    assert get_trace_dir() == configured_dir.resolve(strict=False)
    assert (configured_dir / f"{saved.trace_id}.json").exists()
    assert get_trace(saved.trace_id) is not None


def test_trace_store_rejects_configured_trace_dir_outside_allowed_roots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside_traces"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.setenv(trace_store.TRACE_DIR_ENV, str(outside_dir))
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(LocalPathAccessError):
        get_trace_dir()

    assert not outside_dir.exists()

def test_trace_store_can_save_get_and_list_recent_traces(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")

    trace = build_trace_summary(
        tool_name="run_governance_profile",
        profile_name="metadata_diagnosis_only",
        input_summary={"file_path": "sample.csv"},
    )
    trace.status = "success"
    trace.message = "ok"
    saved = save_trace(trace)

    loaded = get_trace(saved.trace_id)
    recent = list_recent_traces(limit=5)

    assert saved.trace_id
    assert loaded is not None
    assert loaded.tool_name == "run_governance_profile"
    assert recent
    assert recent[0].trace_id == saved.trace_id


def test_trace_store_can_persist_config_asset_operation_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")

    trace = build_trace_summary(
        tool_name="validate_config_asset",
        asset_name="workflow_profiles",
        operation="validate",
        validation_status="valid",
    )
    trace.status = "success"
    trace.message = "validation ok"
    saved = save_trace(trace)
    loaded = get_trace(saved.trace_id)

    assert loaded is not None
    assert loaded.asset_name == "workflow_profiles"
    assert loaded.operation == "validate"
    assert loaded.validation_status == "valid"


def test_trace_store_can_persist_quality_rule_export_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")

    trace = build_trace_summary(
        tool_name="export_confirmed_quality_rules",
        input_summary={"export_format": "json"},
    )
    trace.status = "success"
    trace.export_format = "custom_json"
    trace.exported_rule_count = 3
    trace.confirmed_rule_count = 3
    saved = save_trace(trace)
    loaded = get_trace(saved.trace_id)

    assert loaded is not None
    assert loaded.export_format == "custom_json"
    assert loaded.exported_rule_count == 3
    assert loaded.confirmed_rule_count == 3


def test_trace_store_can_persist_backlog_tracking_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")

    trace = build_trace_summary(
        tool_name="update_governance_backlog_status",
        input_summary={"backlog_id": "backlog_1", "new_status": "accepted"},
    )
    trace.status = "success"
    trace.backlog_item_count = 1
    trace.backlog_status_summary = {"accepted": 1}
    trace.updated_backlog_id = "backlog_1"
    trace.old_status = "proposed"
    trace.new_status = "accepted"
    saved = save_trace(trace)
    loaded = get_trace(saved.trace_id)

    assert loaded is not None
    assert loaded.backlog_item_count == 1
    assert loaded.backlog_status_summary == {"accepted": 1}
    assert loaded.updated_backlog_id == "backlog_1"
    assert loaded.old_status == "proposed"
    assert loaded.new_status == "accepted"


def test_trace_store_can_persist_portfolio_progress_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")

    trace = build_trace_summary(tool_name="assess_governance_portfolio")
    trace.status = "success"
    trace.overdue_count = 2
    trace.blocked_count = 1
    trace.owner_workload_summary = {"business_data_steward": {"total": 3}}
    trace.snapshot_id = "snapshot_1"
    saved = save_trace(trace)
    loaded = get_trace(saved.trace_id)

    assert loaded is not None
    assert loaded.overdue_count == 2
    assert loaded.blocked_count == 1
    assert loaded.owner_workload_summary == {"business_data_steward": {"total": 3}}
    assert loaded.snapshot_id == "snapshot_1"
