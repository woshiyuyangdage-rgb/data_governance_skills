"""Tests for the lightweight execution planner."""

from app.core.agent.execution_planner import ExecutionPlanner
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.interpreted_intent import InterpretedIntent


def _build_intent(profile_name: str, raw_text: str = "demo request") -> InterpretedIntent:
    return InterpretedIntent(
        raw_text=raw_text,
        matched_intent_name="demo_intent",
        matched_profile_name=profile_name,
        confidence=1.0,
    )


def test_execution_planner_builds_diagnosis_plan_with_expected_stages() -> None:
    planner = ExecutionPlanner()
    plan = planner.build_plan(
        _build_intent("metadata_diagnosis_only"),
        GovernanceTaskRequest(
            file_path="sample.csv",
            profile_name="metadata_diagnosis_only",
        ),
    )

    assert plan.stages == ["diagnosis"]
    assert plan.suggested_output_mode == "diagnosis"
    assert plan.validation_passed is True


def test_execution_planner_marks_missing_file_path_as_validation_failed() -> None:
    planner = ExecutionPlanner()
    plan = planner.build_plan(
        _build_intent("metadata_diagnosis_only"),
        GovernanceTaskRequest(
            file_path=None,
            profile_name="metadata_diagnosis_only",
        ),
    )

    assert plan.validation_passed is False
    assert any("file_path" in message for message in plan.validation_messages)


def test_execution_planner_requires_confirmation_for_stg_profile() -> None:
    planner = ExecutionPlanner()
    plan = planner.build_plan(
        _build_intent("diagnosis_mapping_stg"),
        GovernanceTaskRequest(
            file_path="sample.csv",
            profile_name="diagnosis_mapping_stg",
        ),
    )

    assert plan.requires_confirmation is True


def test_execution_planner_allows_auto_run_for_diagnosis_only() -> None:
    planner = ExecutionPlanner()
    plan = planner.build_plan(
        _build_intent("metadata_diagnosis_only"),
        GovernanceTaskRequest(
            file_path="sample.csv",
            profile_name="metadata_diagnosis_only",
        ),
    )

    assert plan.requires_confirmation is False
