"""Core tests for jobs route helpers."""

from pathlib import Path

from app.api.routes_jobs import (
    IntentTextRequest,
    ManualMetadataRequest,
    ManualMetadataRunRequest,
    MetadataMemoryLearningRequest,
    interpret_governance_task,
    learn_metadata_memory_from_file_route,
    list_jobs,
    list_workflow_profiles,
    run_manual_metadata_route,
    run_governance_task_route,
    run_interpreted_governance_task,
    save_manual_metadata_route,
)
from app.core.models.governance_task_request import GovernanceTaskRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_jobs_catalog_lists_unified_task_routes() -> None:
    payload = list_jobs()
    paths = {item["path"] for item in payload["items"]}

    assert "/jobs/run-governance-task" in paths
    assert "/jobs/learn-metadata-memory-from-file" in paths
    assert "/jobs/save-manual-metadata" in paths
    assert "/jobs/run-manual-metadata" in paths
    assert "/jobs/list-workflow-profiles" in paths
    assert "/jobs/interpret-governance-task" in paths
    assert "/jobs/run-interpreted-governance-task" in paths
    assert "/jobs/agent-shell/plan" in paths
    assert "/jobs/agent-shell/resolve-context" in paths
    assert "/jobs/agent-shell/run" in paths
    assert "/jobs/list-tools" in paths
    assert "/jobs/call-tool" in paths
    assert "/jobs/capability-manifest" in paths
    assert "/jobs/tool-schemas/native" in paths
    assert "/jobs/tool-schemas/openai" in paths
    assert "/jobs/tool-schemas/mcp" in paths
    assert "/jobs/invoke-native-tool" in paths
    assert "/jobs/invoke-openai-tool" in paths
    assert "/jobs/trace/{trace_id}" in paths
    assert "/jobs/traces/recent" in paths
    assert "/jobs/config-assets" in paths
    assert "/jobs/config-assets/{asset_name}" in paths
    assert "/jobs/config-assets/{asset_name}/validate" in paths
    assert "/jobs/config-assets/{asset_name}/save" in paths
    assert "/jobs/config-assets/{asset_name}/publish" in paths
    assert "/jobs/learning-health" in paths
    assert "/jobs/learning-health/details" in paths
    assert "/jobs/learning-health/report" in paths
    assert "/jobs/learning-health/report/export" in paths
    assert "/jobs/learning-health/backups" in paths
    assert "/jobs/learning-health/backups/restore" in paths
    assert "/jobs/learning-health/backups/validate" in paths
    assert "/jobs/learning-health/prune-invalid" in paths
    assert "/jobs/learning-health/backup-then-prune-invalid" in paths
    assert "/jobs/learning-health/clear-field-key" in paths
    assert "/jobs/run-p0-plus-mapping-plus-stg-plus-quality" in paths
    assert "/jobs/run-p0-plus-mapping-plus-stg-plus-quality-with-review" in paths
    assert "/jobs/run-quality-only-from-stg" in paths
    assert "/jobs/run-quality-only-from-stg-with-review" in paths
    assert "/jobs/review-quality-rules" in paths
    assert "/jobs/export-confirmed-quality-rules" in paths
    assert "/jobs/build-execution-ready-package" in paths
    assert "/jobs/export-execution-ready-package" in paths
    assert "/jobs/assess-rag-quality" in paths
    assert "/jobs/assess-text-to-sql-readiness" in paths
    assert "/jobs/assess-governance-readiness" in paths
    assert "/jobs/build-governance-work-package" in paths
    assert "/jobs/governance-readiness-summary" in paths
    assert "/jobs/build-governance-backlog" in paths
    assert "/jobs/governance-backlog" in paths
    assert "/jobs/governance-backlog/{backlog_id}/status" in paths
    assert "/jobs/governance-backlog-summary" in paths
    assert "/jobs/assess-governance-portfolio" in paths
    assert "/jobs/generate-progress-snapshot" in paths
    assert "/jobs/governance-progress-snapshots" in paths
    assert "/jobs/governance-portfolio-summary" in paths
    assert "/jobs/execution-package-summary" in paths
    assert "/jobs/quality-rule-review-summary" in paths


def test_list_workflow_profiles_returns_enabled_profiles() -> None:
    profiles = list_workflow_profiles()

    assert profiles
    assert any(profile.name == "metadata_diagnosis_only" for profile in profiles)


def test_run_governance_task_route_returns_structured_response() -> None:
    response = run_governance_task_route(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="metadata_diagnosis_only",
        )
    )

    assert response.profile_name == "metadata_diagnosis_only"
    assert response.status == "success"
    assert response.stages_executed == ["diagnosis"]
    assert response.result.status == "success"


def test_manual_metadata_routes_save_and_run_profile(tmp_path: Path) -> None:
    records = [
        {
            "table_name": "contract_info",
            "table_name_cn": "合同信息",
            "table_description": "融资合同基础信息",
            "business_domain": "finance",
            "field_name": "contract_no",
            "field_name_cn": "合同编号",
            "field_description": "合同唯一编号",
            "data_type": "varchar",
            "nullable": "false",
        }
    ]
    save_response = save_manual_metadata_route(
        ManualMetadataRequest(
            records=records,
            output_dir=str(tmp_path),
            base_filename="route_manual_metadata",
        )
    )
    run_response = run_manual_metadata_route(
        ManualMetadataRunRequest(
            records=records,
            output_dir=str(tmp_path),
            profile_name="metadata_diagnosis_only",
        )
    )

    assert save_response["status"] == "success"
    assert Path(str(save_response["file_path"])).exists()
    assert run_response.status == "success"
    assert run_response.profile_name == "metadata_diagnosis_only"
    assert run_response.result.status == "success"
    assert run_response.result.input_table_count == 1


def test_learn_metadata_memory_from_file_route_writes_local_memory(
    tmp_path: Path,
) -> None:
    response = learn_metadata_memory_from_file_route(
        MetadataMemoryLearningRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            output_dir=str(tmp_path),
        )
    )

    assert response["status"] == "success"
    assert response["field_memory_count"] > 0
    assert response["table_memory_count"] > 0
    assert response["output_dir"] == str(tmp_path)
    assert (tmp_path / "field_completion_memory.csv").exists()
    assert (tmp_path / "table_completion_memory.csv").exists()


def test_run_manual_metadata_route_returns_parser_error_for_empty_input(
    tmp_path: Path,
) -> None:
    response = run_manual_metadata_route(
        ManualMetadataRunRequest(
            records=[],
            output_dir=str(tmp_path),
            profile_name="metadata_diagnosis_only",
        )
    )

    assert response.status == "parser_error"
    assert response.result.status == "parser_error"
    assert "does not contain any rows" in response.message


def test_interpret_governance_task_returns_request_without_execution() -> None:
    response = interpret_governance_task(
        IntentTextRequest(
            text="Run standard mapping and export reports",
            file_path=str(SAMPLE_METADATA_PATH),
        )
    )

    assert response.interpreted_intent.matched_profile_name == "diagnosis_plus_mapping"
    assert response.task_request.export_reports is True
    assert response.task_response is None


def test_run_interpreted_governance_task_executes_router() -> None:
    response = run_interpreted_governance_task(
        IntentTextRequest(
            text="Help me run a quick diagnosis",
            file_path=str(SAMPLE_METADATA_PATH),
        )
    )

    assert response.task_response is not None
    assert response.task_response.status == "success"
    assert response.task_response.result.status == "success"
