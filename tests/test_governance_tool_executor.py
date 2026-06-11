"""Tests for the local governance tool executor."""

from pathlib import Path

from app.core.agent import session_store
from app.core.audit import trace_store
from app.core.audit.trace_store import get_trace
from app.core.tools.governance_tool_executor import GovernanceToolExecutor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def _patch_runtime_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()


def test_executor_can_run_governance_profile_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.run_governance_profile(
        {
            "file_path": str(SAMPLE_METADATA_PATH),
            "profile_name": "metadata_diagnosis_only",
        }
    )

    assert response.status == "success"
    assert response.trace_id is not None
    assert get_trace(response.trace_id) is not None


def test_executor_can_recommend_quality_rules_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.recommend_quality_rules(
        {
            "file_path": str(SAMPLE_METADATA_PATH),
            "profile_name": "diagnosis_mapping_stg_quality",
        }
    )

    assert response.status == "success"
    assert response.trace_id is not None
    assert response.result is not None
    assert response.result["result"]["quality_rule_suggestions"]


def test_executor_can_review_and_export_quality_rules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    review_response = executor.review_quality_rules(
        {
            "quality_rule_suggestions": [
                {
                    "source_table_name": "sales_order",
                    "source_field_name": "order_id",
                    "recommended_field_name": "order_id",
                    "rule_type": "not_null",
                    "rule_expression": "not_null",
                    "severity": "high",
                    "priority": "P1",
                    "recommendation_source": "test",
                }
            ],
            "review_inputs": {
                "sales_order.order_id.not_null": {"review_action": "accept"}
            },
        }
    )
    export_response = executor.export_confirmed_quality_rules(
        {
            "confirmed_quality_rules": review_response.result["confirmed_quality_rules"],
            "export_format": "json",
            "output_dir": str(tmp_path / "rule_exports"),
            "base_filename": "executor_quality_rules",
        }
    )

    assert review_response.status == "success"
    assert review_response.result["quality_rule_review_summary"]["confirmed_count"] == 1
    assert export_response.status == "success"
    assert export_response.result["rule_export_results"][0]["rule_count"] == 1
    trace = get_trace(export_response.trace_id)
    assert trace is not None
    assert trace.export_format == "custom_json"
    assert trace.confirmed_rule_count == 1


def test_executor_can_build_and_export_execution_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()
    confirmed_rules = [
        {
            "source_table_name": "sales_order",
            "source_field_name": "order_id",
            "recommended_field_name": "order_id",
            "rule_type": "not_null",
            "rule_expression": "not_null",
            "severity": "high",
            "priority": "P1",
            "confirmation_source": "override_accept",
        }
    ]

    build_response = executor.build_execution_ready_package(
        {
            "confirmed_quality_rules": confirmed_rules,
            "profile_name": "executor_package_profile",
        }
    )
    export_response = executor.export_execution_ready_package(
        {
            "execution_ready_package": build_response.result["execution_ready_package"],
            "export_format": "manifest",
            "output_dir": str(tmp_path / "execution_packages"),
            "base_filename": "executor_execution_package",
        }
    )

    assert build_response.status == "success"
    assert build_response.result["execution_package_summary"]["rule_count"] == 1
    assert export_response.status == "success"
    assert export_response.result["execution_package_export_results"][0]["rule_count"] == 1
    trace = get_trace(export_response.trace_id)
    assert trace is not None
    assert trace.package_rule_count == 1
    assert trace.exported_package_path is not None


def test_executor_can_assess_rag_quality_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.assess_rag_quality(
        {
            "documents": [
                {
                    "document_id": "policy_v1",
                    "title": "Permission Policy",
                    "source": "wiki",
                    "version": "v1",
                    "status": "deprecated",
                }
            ],
            "chunks": [
                {
                    "chunk_id": "chunk_1",
                    "document_id": "policy_v1",
                    "content": "secret rule",
                    "permission_label": "public",
                }
            ],
        }
    )

    assert response.status == "success"
    assert response.trace_id is not None
    assert response.result is not None
    assert response.result["rag_quality_summary"]["issue_count"] >= 1
    trace = get_trace(response.trace_id)
    assert trace is not None
    assert trace.operation == "rag_quality_assessment"


def test_executor_can_assess_text_to_sql_readiness_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.assess_text_to_sql_readiness(
        {
            "tables": [
                {
                    "table_name": "tmp_order_log",
                    "table_description": "tmp",
                    "fields": [
                        {"field_name": "status", "field_description": "status"},
                    ],
                }
            ]
        }
    )

    assert response.status == "success"
    assert response.trace_id is not None
    assert response.result is not None
    assert response.result["text_to_sql_readiness_summary"]["issue_count"] >= 1
    trace = get_trace(response.trace_id)
    assert trace is not None
    assert trace.operation == "text_to_sql_readiness_assessment"


def test_executor_can_preview_agent_plan_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))

    response = executor.preview_agent_plan(
        {
            "text": "Help me inspect this file",
            "session_id": session.session_id,
        }
    )

    assert response.trace_id is not None
    assert response.result is not None
    assert response.result["task_request"]["file_path"] == str(SAMPLE_METADATA_PATH)


def test_executor_can_run_agent_task_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.run_agent_task(
        {
            "text": "Help me inspect this file",
            "file_path": str(SAMPLE_METADATA_PATH),
            "force_run": True,
        }
    )

    assert response.trace_id is not None
    assert response.status == "executed_successfully"
    assert get_trace(response.trace_id) is not None


def test_executor_can_resolve_governance_context_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))

    response = executor.resolve_governance_context(
        {
            "text": "Help me inspect this file",
            "session_id": session.session_id,
        }
    )

    assert response.trace_id is not None
    assert response.result is not None
    assert response.result["resolved_context"]["resolved_file_path"] == str(
        SAMPLE_METADATA_PATH
    )


def test_executor_can_list_config_assets_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.list_config_assets({})

    assert response.trace_id is not None
    assert response.status == "success"
    assert isinstance(response.result, list)
    assert any(item["asset_name"] == "workflow_profiles" for item in response.result)

    trace = get_trace(response.trace_id)
    assert trace is not None
    assert trace.operation == "list"


def test_executor_can_validate_config_asset_and_record_trace(
    tmp_path: Path,
    monkeypatch,
    isolated_control_plane_runtime: Path,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.validate_config_asset({"asset_name": "workflow_profiles"})

    assert response.trace_id is not None
    assert response.result is not None
    assert response.result["asset_name"] == "workflow_profiles"

    trace = get_trace(response.trace_id)
    assert trace is not None
    assert trace.asset_name == "workflow_profiles"
    assert trace.operation == "validate"


def test_executor_can_report_learning_health_and_record_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()

    response = executor.learning_health({})

    assert response.trace_id is not None
    assert response.status == "success"
    assert response.result is not None
    assert "total_memory_count" in response.result
    assert "quality_rules" in response.result

    trace = get_trace(response.trace_id)
    assert trace is not None
    assert trace.operation == "learning_health"


def test_executor_can_rebuild_review_learning_with_explicit_memory_types(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_dirs(tmp_path, monkeypatch)
    executor = GovernanceToolExecutor()
    calls: list[dict[str, object]] = []

    class FakeLearningHealthService:
        def rebuild_review_learning(
            self,
            memory_types: list[str] | None = None,
            *,
            create_backup: bool = True,
        ) -> dict[str, object]:
            calls.append(
                {
                    "memory_types": list(memory_types or []),
                    "create_backup": create_backup,
                }
            )
            return {
                "status": "success",
                "memory_types": list(memory_types or []),
                "backup": None,
                "results": {},
                "total_review_record_count": 2,
                "total_learned_count": 1,
                "summary": "Review learning rebuilt for test.",
            }

    executor.learning_health_service = FakeLearningHealthService()

    response = executor.rebuild_review_learning(
        {
            "memory_types": ["standard_mapping", "quality_rules"],
            "create_backup": False,
        }
    )

    assert response.status == "success"
    assert response.result is not None
    assert response.result["total_learned_count"] == 1
    assert calls == [
        {
            "memory_types": ["standard_mapping", "quality_rules"],
            "create_backup": False,
        }
    ]

    trace = get_trace(response.trace_id)
    assert trace is not None
    assert trace.operation == "rebuild_review_learning"
