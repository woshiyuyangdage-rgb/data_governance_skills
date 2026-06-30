"""Tests for syncing workflow results into project workspaces."""

from pathlib import Path

from app.core.governance import project_workspace_service as workspace_service
from app.core.governance import project_workspace_sync_service as sync_service
from app.core.models.backlog_summary import BacklogSummary
from app.core.models.confirmation_workbook_result import ConfirmationWorkbookResult
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.governance_delivery_package_result import (
    GovernanceDeliveryPackageResult,
)
from app.core.models.review_summary import ReviewSummary
from app.core.models.rule_export_result import RuleExportResult
from app.core.models.workflow_result import WorkflowResult


def _isolate_workspace_store(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(workspace_service, "PROJECT_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(
        workspace_service,
        "PROJECT_WORKSPACE_INDEX_PATH",
        tmp_path / "index.json",
    )
    monkeypatch.setattr(
        workspace_service,
        "PROJECT_WORKSPACE_SNAPSHOT_DIR",
        tmp_path / "_snapshots",
    )


def test_sync_workflow_result_records_run_reviews_and_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace_store(monkeypatch, tmp_path)
    workspace = workspace_service.create_project_workspace("Customer governance")
    workflow_result = WorkflowResult(
        input_table_count=2,
        issue_count=3,
        task_count=4,
        status="success",
        review_summary=ReviewSummary(
            accepted_count=2,
            rejected_count=1,
            edited_count=1,
            manual_review_count=3,
            total_reviewed_count=7,
        ),
        quality_review_queue_summary={
            "total_rule_count": 5,
            "low_confidence_rule_count": 2,
        },
        backlog_summary=BacklogSummary(
            total_items=5,
            by_status={"proposed": 2, "blocked": 1, "completed": 2},
            blocked_count=1,
            completed_count=2,
        ),
        rule_export_results=[
            RuleExportResult(
                export_format="json",
                output_path="outputs/rules/customer_rules.json",
                rule_count=5,
                status="success",
            )
        ],
        execution_package_export_results=[
            ExecutionPackageExportResult(
                export_format="zip",
                output_path="outputs/execution/customer_package.zip",
                package_id="pkg-1",
                rule_count=5,
                status="success",
            )
        ],
        confirmation_workbook_results=[
            ConfirmationWorkbookResult(
                workbook_type="quality_rules",
                output_path="outputs/workbooks/quality.xlsx",
                row_count=5,
                status="success",
            )
        ],
        governance_delivery_package_result=GovernanceDeliveryPackageResult(
            package_name="customer_delivery",
            output_dir="outputs/delivery/customer",
            generated_files={
                "manifest": "outputs/delivery/customer/manifest.json",
                "reports": ["outputs/delivery/customer/report.md"],
            },
            status="success",
        ),
    )

    result = sync_service.sync_workflow_result_to_project_workspace(
        workspace.workspace_id,
        workflow_result,
        workflow_profile="full_governance_delivery_package",
        input_file_path="inputs/customer.csv",
    )

    loaded = workspace_service.load_project_workspace(workspace.workspace_id)
    assert loaded is not None
    assert loaded.runs[0].workflow_profile == "full_governance_delivery_package"
    assert loaded.runs[0].input_file_path == "inputs/customer.csv"
    assert loaded.runs[0].result_summary["issue_count"] == 3
    assert result["synced_review_queue_count"] == 3
    assert result["attached_artifact_count"] == 6
    assert len(loaded.artifacts) == 6
    assert len(loaded.runs[0].artifact_ids) == 6

    reviews = {review.queue_name: review for review in loaded.review_states}
    assert reviews["manual_review"].pending_count == 3
    assert reviews["quality_rules"].pending_count == 2
    assert reviews["governance_backlog"].pending_count == 3
    assert reviews["governance_backlog"].needs_business_confirmation_count == 1


def test_sync_workflow_artifacts_skips_existing_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace_store(monkeypatch, tmp_path)
    workspace = workspace_service.create_project_workspace("Rule exports")
    workflow_result = WorkflowResult(
        rule_export_results=[
            RuleExportResult(
                export_format="json",
                output_path="outputs/rules/customer_rules.json",
                rule_count=5,
                status="success",
            )
        ],
    )

    first = sync_service.sync_workflow_artifacts_to_project_workspace(
        workspace.workspace_id,
        workflow_result,
    )
    second = sync_service.sync_workflow_artifacts_to_project_workspace(
        workspace.workspace_id,
        workflow_result,
    )

    loaded = workspace_service.load_project_workspace(workspace.workspace_id)
    assert loaded is not None
    assert first["attached_artifact_count"] == 1
    assert second["attached_artifact_count"] == 0
    assert second["skipped_artifact_count"] == 1
    assert len(loaded.artifacts) == 1
