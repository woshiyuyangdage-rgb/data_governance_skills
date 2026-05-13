"""Tests for intent interpretation plus task execution service."""

from pathlib import Path

from app.core.intent.intent_task_service import (
    interpret_and_build_request,
    interpret_and_run_task,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_interpret_only_returns_task_request() -> None:
    result = interpret_and_build_request(
        "给我做标准映射并导出报告",
        str(SAMPLE_METADATA_PATH),
    )

    assert result.interpreted_intent.matched_profile_name == "diagnosis_plus_mapping"
    assert result.task_request.export_reports is True
    assert result.task_response is None


def test_interpret_and_run_returns_task_response() -> None:
    result = interpret_and_run_task(
        "帮我做一次快速诊断",
        str(SAMPLE_METADATA_PATH),
    )

    assert result.task_response is not None
    assert result.task_response.status == "success"
    assert result.task_response.result.status == "success"


def test_interpret_and_run_without_file_path_returns_clear_failure() -> None:
    result = interpret_and_run_task("帮我做一次快速诊断")

    assert result.task_response is not None
    assert result.task_response.status == "failed"
    assert "file_path" in result.task_response.message
