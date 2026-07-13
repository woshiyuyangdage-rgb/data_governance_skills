"""Readiness and delivery route tests."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.routes_jobs import (
    GovernanceReadinessAssessmentRequest,
    GovernanceWorkPackageBuildRequest,
    assess_governance_readiness_route,
    build_governance_work_package_route,
    governance_readiness_summary_route,
)
from app.core.models.issue import Issue
from app.core.models.workflow_result import WorkflowResult
from app.core.utils import file_utils


def test_governance_readiness_and_work_package_routes(tmp_path: Path) -> None:
    workflow_result = WorkflowResult(
        status="success",
        message="route readiness test",
        issues=[
            Issue(
                issue_id="i1",
                object_type="field",
                object_name="sales_order.order_id",
                issue_type="missing_field_description",
                severity="medium",
            )
        ],
    )

    readiness_response = assess_governance_readiness_route(
        GovernanceReadinessAssessmentRequest(workflow_result=workflow_result)
    )
    work_package_response = build_governance_work_package_route(
        GovernanceWorkPackageBuildRequest(
            workflow_result=workflow_result,
            export_package=True,
            output_dir=str(tmp_path),
            base_filename="api_governance_work_package",
        )
    )
    summary_response = governance_readiness_summary_route()

    assert readiness_response["readiness_scores"]
    assert readiness_response["ai_ready_scores"]
    assert "ai_ready_summary" in readiness_response
    assert readiness_response["governance_gaps"]
    assert work_package_response["governance_work_package"]["package_name"]
    assert work_package_response["ai_ready_scores"]
    assert work_package_response["remediation_actions"]
    assert Path(
        work_package_response["exported_files"]["governance_work_package"]
    ).exists()
    assert "dimensions" in summary_response
    assert "ai_ready_dimensions" in summary_response


def test_governance_work_package_route_rejects_output_dir_outside_allowed_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)
    workflow_result = WorkflowResult(
        status="success",
        message="route readiness test",
        issues=[
            Issue(
                issue_id="i1",
                object_type="field",
                object_name="sales_order.order_id",
                issue_type="missing_field_description",
                severity="medium",
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        build_governance_work_package_route(
            GovernanceWorkPackageBuildRequest(
                workflow_result=workflow_result,
                export_package=True,
                output_dir=str(outside_dir),
                base_filename="outside_governance_work_package",
            )
        )

    assert exc_info.value.status_code == 400
    assert "outside allowed local roots" in str(exc_info.value.detail)
    assert not outside_dir.exists()
