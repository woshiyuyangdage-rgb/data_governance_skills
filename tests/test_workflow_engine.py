"""Workflow engine tests for the local MVP pipeline."""

from pathlib import Path

from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_p0_pipeline_from_file,
    run_p0_plus_mapping_from_file,
    run_p0_plus_mapping_plus_stg_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_with_review_from_file,
)
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.stg_review_record import StgReviewRecord
from app.core.review import override_store
from app.core.parser.loader import load_metadata_file
from app.core.orchestrator.workflow_engine import WorkflowEngine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_workflow_engine_can_be_instantiated() -> None:
    engine = WorkflowEngine()
    assert engine.metadata_completeness_check.skill_name == "metadata_completeness_check"


def test_run_p0_pipeline_with_empty_input_returns_empty_result() -> None:
    engine = WorkflowEngine()
    result = engine.run_p0_pipeline([])

    assert isinstance(result, WorkflowResult)
    assert result.status == "empty"
    assert result.issue_count == 0
    assert result.task_count == 0


def test_run_p0_pipeline_from_file_returns_workflow_result() -> None:
    result = run_p0_pipeline_from_file(str(SAMPLE_METADATA_PATH))

    assert isinstance(result, WorkflowResult)
    assert result.status == "success"
    assert result.input_table_count == 4
    assert result.issue_count >= 1
    assert result.task_count >= 1
    assert "completeness_output" in result.skill_outputs
    assert "diagnosis_output" in result.skill_outputs
    assert "semantic_enrichment_output" in result.skill_outputs
    assert result.field_description_suggestions
    assert result.table_semantic_summaries
    assert result.semantic_enrichment_summary


def test_run_p0_pipeline_from_missing_file_returns_parser_error() -> None:
    result = run_p0_pipeline_from_file("missing_metadata.csv")

    assert isinstance(result, WorkflowResult)
    assert result.status == "parser_error"
    assert "does not exist" in result.message


def test_run_p0_plus_mapping_from_file_returns_mapping_results() -> None:
    result = run_p0_plus_mapping_from_file(str(SAMPLE_METADATA_PATH))

    assert isinstance(result, WorkflowResult)
    assert result.status == "success"
    assert result.mapping_results
    assert result.mapping_summary
    assert result.field_description_suggestions
    assert "standard_mapping_output" in result.skill_outputs


def test_run_p0_plus_mapping_plus_stg_from_file_returns_stg_results() -> None:
    result = run_p0_plus_mapping_plus_stg_from_file(str(SAMPLE_METADATA_PATH))

    assert isinstance(result, WorkflowResult)
    assert result.status == "success"
    assert result.mapping_results
    assert result.stg_suggestions
    assert result.stg_field_suggestions
    assert result.stg_summary
    assert "stg_structure_output" in result.skill_outputs


def test_run_p0_plus_mapping_plus_stg_plus_quality_from_file_returns_quality_results() -> None:
    result = run_p0_plus_mapping_plus_stg_plus_quality_from_file(str(SAMPLE_METADATA_PATH))

    assert isinstance(result, WorkflowResult)
    assert result.status == "success"
    assert result.stg_field_suggestions
    assert result.quality_rule_suggestions
    assert result.quality_rule_summary
    assert "quality_rule_output" in result.skill_outputs


def test_run_stg_only_from_mapping_returns_mapping_and_stg_without_tasks() -> None:
    engine = WorkflowEngine()
    tables = load_metadata_file(str(SAMPLE_METADATA_PATH))

    result = engine.run_stg_only_from_mapping(tables)

    assert isinstance(result, WorkflowResult)
    assert result.status == "success"
    assert result.mapping_results
    assert result.stg_field_suggestions
    assert result.task_count == 0


def test_run_p0_plus_mapping_plus_stg_with_review_applies_confirmed_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "STG_OVERRIDES_PATH",
        tmp_path / "stg_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )

    override_store.save_mapping_review_records(
        [
            MappingReviewRecord(
                table_name="Sales Order Header",
                field_name="Order__ID",
                original_recommended_standard_code="transaction_id",
                final_standard_code="audit_log_id",
                review_action="edit",
                reviewer_note="demo mapping edit",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ]
    )
    override_store.save_stg_review_records(
        [
            StgReviewRecord(
                source_table_name="ods_customer_snapshot",
                source_field_name="snapshot_dt",
                original_recommended_stg_field_name="snapshot_date",
                final_stg_field_name="snapshot_business_date",
                original_recommended_data_type="date",
                final_data_type="timestamp",
                review_action="edit",
                reviewer_note="demo stg edit",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ]
    )

    result = run_p0_plus_mapping_plus_stg_with_review_from_file(str(SAMPLE_METADATA_PATH))

    assert isinstance(result, WorkflowResult)
    assert result.status == "success"
    assert result.confirmed_mapping_results
    assert result.confirmed_stg_suggestions
    assert any(
        item.recommended_standard_code == "audit_log_id"
        for item in result.confirmed_mapping_results
    )
    assert any(
        item.recommended_stg_field_name == "snapshot_business_date"
        for item in result.confirmed_stg_suggestions
    )
    assert result.review_summary is not None


def test_governance_readiness_assessment_includes_ai_ready_scores() -> None:
    engine = WorkflowEngine()
    tables = load_metadata_file(str(SAMPLE_METADATA_PATH))

    result = engine.run_governance_readiness_assessment(tables)

    assert result.readiness_scores
    assert result.ai_ready_scores
    assert result.ai_ready_summary["ai_ready_score_count"] == len(result.ai_ready_scores)
    assert "ai_ready_assessment_output" in result.skill_outputs
