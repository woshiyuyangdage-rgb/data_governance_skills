"""Lightweight tests for jobs route helpers."""

import json
from pathlib import Path

from app.api.routes_jobs import (
    AgentShellPlanRequest,
    AgentShellRunRequest,
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
    ConfigAssetSaveRequest,
    ConfirmedQualityRuleExportRequest,
    ExecutionPackageBuildRequest,
    ExecutionPackageExportRequest,
    GovernanceBacklogBuildRequest,
    GovernanceBacklogStatusUpdateRequest,
    GovernancePortfolioAssessmentRequest,
    GovernanceReadinessAssessmentRequest,
    GovernanceWorkPackageBuildRequest,
    IntentTextRequest,
    ProgressSnapshotRequest,
    assess_governance_portfolio_route,
    assess_governance_readiness_route,
    agent_shell_plan,
    agent_shell_resolve_context,
    agent_shell_run,
    agent_shell_session,
    capability_manifest_route,
    call_tool_route,
    get_config_asset_route,
    get_trace_route,
    invoke_native_tool_route,
    invoke_openai_tool_route,
    interpret_governance_task,
    list_config_assets_route,
    list_jobs,
    list_recent_traces_route,
    list_tools_route,
    list_workflow_profiles,
    mcp_tool_manifest_route,
    native_tool_schemas_route,
    openai_tool_schemas_route,
    publish_config_asset_route,
    quality_rule_review_summary_route,
    review_quality_rules_route,
    run_governance_task_route,
    run_interpreted_governance_task,
    save_config_asset_route,
    export_confirmed_quality_rules_route,
    build_execution_ready_package_route,
    build_governance_backlog_route,
    build_governance_work_package_route,
    export_execution_ready_package_route,
    execution_package_summary_route,
    governance_backlog_route,
    governance_backlog_summary_route,
    governance_portfolio_summary_route,
    governance_progress_snapshots_route,
    governance_readiness_summary_route,
    generate_progress_snapshot_route,
    update_governance_backlog_status_route,
    validate_config_asset_route,
    QualityRuleReviewRequest,
)
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.agent import session_store
from app.core.audit import trace_store
from app.core.control_plane import control_plane_service as control_plane_module
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.issue import Issue
from app.core.models.tool_call_request import ToolCallRequest
from app.core.models.workflow_result import WorkflowResult
from app.core.governance import backlog_store
from app.core.governance import progress_snapshot_service

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def _setup_control_plane_runtime(tmp_path: Path, monkeypatch) -> None:
    asset_file = tmp_path / "workflow_profiles.yaml"
    asset_file.write_text(
        "\n".join(
            [
                "profiles:",
                "  - name: metadata_diagnosis_only",
                "    enabled: true",
                "    description: Run metadata diagnosis only",
                "    stages:",
                "      - diagnosis",
            ]
        ),
        encoding="utf-8",
    )
    asset_registry_path = tmp_path / "asset_registry.json"
    asset_registry_path.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "asset_name": "workflow_profiles",
                        "asset_type": "yaml",
                        "file_path": str(asset_file),
                        "description": "Workflow profile config",
                        "editable": True,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    config_status_path = tmp_path / "config_status.json"
    config_status_path.write_text(
        json.dumps(
            {
                "statuses": [
                    {
                        "asset_name": "workflow_profiles",
                        "asset_type": "yaml",
                        "file_path": str(asset_file),
                        "current_status": "published",
                        "last_validated_at": None,
                        "last_published_at": None,
                        "last_error_message": None,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(control_plane_module, "CONTROL_PLANE_DIR", tmp_path)
    monkeypatch.setattr(control_plane_module, "ASSET_REGISTRY_PATH", asset_registry_path)
    monkeypatch.setattr(control_plane_module, "CONFIG_STATUS_PATH", config_status_path)
    monkeypatch.setattr(control_plane_module, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(control_plane_module, "SNAPSHOT_DIR", tmp_path / "snapshots")


def test_jobs_catalog_lists_unified_task_routes() -> None:
    payload = list_jobs()
    paths = {item["path"] for item in payload["items"]}

    assert "/jobs/run-governance-task" in paths
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
    assert "/jobs/run-p0-plus-mapping-plus-stg-plus-quality" in paths
    assert "/jobs/run-p0-plus-mapping-plus-stg-plus-quality-with-review" in paths
    assert "/jobs/run-quality-only-from-stg" in paths
    assert "/jobs/run-quality-only-from-stg-with-review" in paths
    assert "/jobs/review-quality-rules" in paths
    assert "/jobs/export-confirmed-quality-rules" in paths
    assert "/jobs/build-execution-ready-package" in paths
    assert "/jobs/export-execution-ready-package" in paths
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


def test_list_tools_route_returns_enabled_tools() -> None:
    tools = list_tools_route()

    assert tools
    assert any(tool.name == "run_governance_profile" for tool in tools)
    assert any(tool.name == "list_config_assets" for tool in tools)
    assert any(tool.name == "recommend_quality_rules" for tool in tools)
    assert any(tool.name == "recommend_quality_intelligence" for tool in tools)
    assert any(tool.name == "review_quality_rules" for tool in tools)
    assert any(tool.name == "batch_review_quality_rules" for tool in tools)
    assert any(tool.name == "export_confirmed_quality_rules" for tool in tools)
    assert any(tool.name == "build_execution_ready_package" for tool in tools)
    assert any(tool.name == "export_execution_ready_package" for tool in tools)
    assert any(tool.name == "assess_governance_readiness" for tool in tools)
    assert any(tool.name == "build_governance_work_package" for tool in tools)
    assert any(tool.name == "build_governance_backlog" for tool in tools)
    assert any(tool.name == "update_governance_backlog_status" for tool in tools)
    assert any(tool.name == "list_governance_backlog_items" for tool in tools)
    assert any(tool.name == "assess_governance_portfolio" for tool in tools)
    assert any(tool.name == "generate_progress_snapshot" for tool in tools)
    assert any(tool.name == "list_governance_progress_snapshots" for tool in tools)


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


def test_agent_shell_plan_returns_preview_result() -> None:
    response = agent_shell_plan(
        AgentShellPlanRequest(
            text="Generate STG structure suggestions",
            file_path=str(SAMPLE_METADATA_PATH),
        )
    )

    assert response.execution_plan.profile_name == "diagnosis_mapping_stg"
    assert response.task_response is None


def test_agent_shell_resolve_context_returns_resolved_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()
    session = session_store.create_session()
    session_store.set_last_uploaded_file(session.session_id, str(SAMPLE_METADATA_PATH))

    response = agent_shell_resolve_context(
        AgentShellPlanRequest(
            text="Help me inspect this file",
            session_id=session.session_id,
        )
    )

    assert response.resolved_context is not None
    assert response.task_request.file_path == str(SAMPLE_METADATA_PATH)
    assert response.execution_plan.validation_passed is True


def test_agent_shell_run_can_execute_and_expose_session() -> None:
    response = agent_shell_run(
        AgentShellRunRequest(
            text="Help me inspect this file",
            file_path=str(SAMPLE_METADATA_PATH),
        )
    )

    assert response.status == "executed_successfully"
    assert response.task_response is not None
    assert response.session_id is not None

    session = agent_shell_session(response.session_id)
    assert session is not None
    assert session.last_task_response is not None


def test_call_tool_route_returns_traceable_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    response = call_tool_route(
        ToolCallRequest(
            tool_name="run_governance_profile",
            arguments={
                "file_path": str(SAMPLE_METADATA_PATH),
                "profile_name": "metadata_diagnosis_only",
            },
        )
    )

    assert response.status == "success"
    assert response.trace_id is not None

    trace = get_trace_route(response.trace_id)
    assert trace is not None
    assert trace.tool_name == "run_governance_profile"

    recent = list_recent_traces_route(limit=10)
    assert any(item.trace_id == response.trace_id for item in recent)


def test_adapter_manifest_routes_return_expected_payloads() -> None:
    manifest = capability_manifest_route()
    native_schemas = native_tool_schemas_route()
    openai_schemas = openai_tool_schemas_route()
    mcp_manifest = mcp_tool_manifest_route()

    assert manifest.service_name == "data_governance_skills"
    assert native_schemas
    assert openai_schemas
    assert "tools" in mcp_manifest


def test_adapter_invoke_routes_return_traceable_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(session_store, "SESSION_SNAPSHOT_DIR", tmp_path / "agent_sessions")
    session_store.clear_session_store()

    native_result = invoke_native_tool_route(
        NativeToolInvokeRequest(
            tool_name="run_governance_profile",
            arguments={
                "file_path": str(SAMPLE_METADATA_PATH),
                "profile_name": "metadata_diagnosis_only",
            },
        )
    )
    openai_result = invoke_openai_tool_route(
        OpenAIToolInvokeRequest(
            function_name="validate_config_asset",
            arguments_json={"asset_name": "workflow_profiles"},
        )
    )

    assert native_result.trace_id is not None
    assert native_result.status == "success"
    assert openai_result.trace_id is not None


def test_config_asset_routes_can_list_get_and_validate_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _setup_control_plane_runtime(tmp_path, monkeypatch)

    assets = list_config_assets_route()
    payload = get_config_asset_route("workflow_profiles")
    validation = validate_config_asset_route("workflow_profiles")

    assert assets
    assert assets[0]["asset_name"] == "workflow_profiles"
    assert payload["asset"]["asset_name"] == "workflow_profiles"
    assert validation.is_valid is True


def test_config_asset_routes_can_save_and_publish_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _setup_control_plane_runtime(tmp_path, monkeypatch)

    save_result = save_config_asset_route(
        "workflow_profiles",
        ConfigAssetSaveRequest(
            content="\n".join(
                [
                    "profiles:",
                    "  - name: metadata_diagnosis_only",
                    "    enabled: true",
                    "    description: Run metadata diagnosis only",
                    "    stages:",
                    "      - diagnosis",
                    "  - name: mapping_only",
                    "    enabled: true",
                    "    description: Run mapping only",
                    "    stages:",
                    "      - mapping",
                ]
            )
        ),
    )
    publish_result = publish_config_asset_route("workflow_profiles")

    assert save_result.status == "draft"
    assert save_result.backup_path is not None
    assert publish_result.status == "published"


def test_quality_rule_review_and_summary_routes() -> None:
    confirmed_rule = ConfirmedQualityRule(
        source_table_name="sales_order",
        source_field_name="order_id",
        recommended_field_name="order_id",
        rule_type="not_null",
        rule_expression="not_null",
        severity="high",
        priority="P1",
        confirmation_source="override_accept",
    )
    response = review_quality_rules_route(
        QualityRuleReviewRequest(
            quality_rule_suggestions=[
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
            review_inputs={"sales_order.order_id.not_null": {"review_action": "accept"}},
            save_overrides=False,
        )
    )
    summary = quality_rule_review_summary_route()

    assert response["quality_rule_review_summary"]["confirmed_count"] == 1
    assert response["confirmed_quality_rules"][0]["rule_type"] == confirmed_rule.rule_type
    assert "accepted_count" in summary


def test_quality_rule_review_route_accepts_cross_field_rules() -> None:
    response = review_quality_rules_route(
        QualityRuleReviewRequest(
            cross_field_quality_rules=[
                CrossFieldQualityRule(
                    source_table_name="sales_order",
                    field_group=["start_date", "end_date"],
                    rule_type="temporal_order",
                    rule_expression="start_date <= end_date",
                    severity="medium",
                    confidence=1.0,
                    review_priority="medium_review_priority",
                    recommendation_source="cross_field_pattern",
                    match_basis="start_date/end_date",
                    reason="Start date should not be later than end date.",
                )
            ],
            review_inputs={},
            save_overrides=False,
        )
    )

    assert response["quality_rule_review_summary"]["confirmed_count"] == 1
    assert response["confirmed_quality_rules"][0]["rule_scope"] == "cross_field"
    assert response["confirmed_quality_rules"][0]["field_group"] == [
        "start_date",
        "end_date",
    ]


def test_export_confirmed_quality_rules_route(tmp_path: Path) -> None:
    response = export_confirmed_quality_rules_route(
        ConfirmedQualityRuleExportRequest(
            export_format="json",
            confirmed_quality_rules=[
                ConfirmedQualityRule(
                    source_table_name="sales_order",
                    source_field_name="order_id",
                    recommended_field_name="order_id",
                    rule_type="not_null",
                    rule_expression="not_null",
                    severity="high",
                    priority="P1",
                    confirmation_source="override_accept",
                )
            ],
            output_dir=str(tmp_path),
            base_filename="api_quality_rules",
        )
    )

    assert response["confirmed_rule_count"] == 1
    export_result = response["rule_export_results"][0]
    assert export_result["rule_count"] == 1
    assert Path(export_result["output_path"]).exists()


def test_execution_package_build_and_export_routes(tmp_path: Path) -> None:
    confirmed_rule = ConfirmedQualityRule(
        source_table_name="sales_order",
        source_field_name="order_id",
        recommended_field_name="order_id",
        rule_type="not_null",
        rule_expression="not_null",
        severity="high",
        priority="P1",
        confirmation_source="override_accept",
    )
    build_response = build_execution_ready_package_route(
        ExecutionPackageBuildRequest(
            confirmed_quality_rules=[confirmed_rule],
            profile_name="api_package_profile",
        )
    )
    package_payload = build_response["execution_ready_package"]
    export_response = export_execution_ready_package_route(
        ExecutionPackageExportRequest(
            export_format="manifest",
            execution_ready_package=package_payload,
            output_dir=str(tmp_path),
            base_filename="api_execution_package",
        )
    )
    summary_response = execution_package_summary_route()

    assert build_response["execution_package_summary"]["rule_count"] == 1
    assert package_payload["rules"][0]["rule_id"].startswith("rule_")
    export_result = export_response["execution_package_export_results"][0]
    assert export_result["rule_count"] == 1
    assert Path(export_result["output_path"]).exists()
    assert "supported_export_formats" in summary_response


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
    assert readiness_response["governance_gaps"]
    assert work_package_response["governance_work_package"]["package_name"]
    assert work_package_response["remediation_actions"]
    assert Path(
        work_package_response["exported_files"]["governance_work_package"]
    ).exists()
    assert "dimensions" in summary_response


def test_governance_backlog_routes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    backlog_dir = tmp_path / "governance_backlog"
    monkeypatch.setattr(backlog_store, "BACKLOG_DIR", backlog_dir)
    monkeypatch.setattr(
        backlog_store,
        "BACKLOG_ITEMS_PATH",
        backlog_dir / "backlog_items.json",
    )
    monkeypatch.setattr(
        backlog_store,
        "BACKLOG_SNAPSHOTS_DIR",
        backlog_dir / "backlog_snapshots",
    )

    build_response = build_governance_backlog_route(
        GovernanceBacklogBuildRequest(
            remediation_actions=[
                {
                    "object_type": "table",
                    "object_name": "sales_order",
                    "gap_type": "standard_mapping_gap",
                    "action": "Review and confirm standard mappings",
                    "owner_role": "business_data_steward",
                    "priority": "key_tracking",
                }
            ],
            persist=True,
        )
    )
    backlog_id = build_response["governance_backlog_items"][0]["backlog_id"]
    list_response = governance_backlog_route(status="proposed")
    update_response = update_governance_backlog_status_route(
        backlog_id,
        GovernanceBacklogStatusUpdateRequest(
            new_status="accepted",
            note="Accepted for route test.",
        ),
    )
    summary_response = governance_backlog_summary_route()

    assert build_response["backlog_summary"]["total_items"] == 1
    assert list_response["governance_backlog_items"][0]["backlog_id"] == backlog_id
    assert update_response["update_result"]["status"] == "success"
    assert summary_response["backlog_summary"]["by_status"] == {"accepted": 1}


def test_governance_portfolio_and_snapshot_routes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(trace_store, "TRACE_DIR", tmp_path / "execution_traces")
    monkeypatch.setattr(
        progress_snapshot_service,
        "PROGRESS_SNAPSHOT_DIR",
        tmp_path / "progress_snapshots",
    )
    backlog_item = {
        "backlog_id": "backlog_portfolio_1",
        "object_type": "table",
        "object_name": "sales_order",
        "gap_type": "standard_mapping_gap",
        "action": "Review and confirm standard mappings",
        "owner_role": "business_data_steward",
        "priority": "key_tracking",
        "status": "proposed",
        "created_at": "2026-05-01T00:00:00",
    }
    sla_status = {
        "backlog_id": "backlog_portfolio_1",
        "due_date": "2026-05-18",
        "age_days": 19,
        "overdue_days": 2,
        "is_overdue": True,
        "sla_status": "overdue",
    }

    portfolio_response = assess_governance_portfolio_route(
        GovernancePortfolioAssessmentRequest(
            governance_backlog_items=[backlog_item],
            backlog_sla_statuses=[sla_status],
        )
    )
    snapshot_response = generate_progress_snapshot_route(
        ProgressSnapshotRequest(
            governance_backlog_items=[backlog_item],
            backlog_sla_statuses=[sla_status],
            save=True,
        )
    )
    snapshots_response = governance_progress_snapshots_route()
    summary_response = governance_portfolio_summary_route()

    assert portfolio_response["governance_portfolio_summary"]["overdue_count"] == 1
    assert portfolio_response["progress_snapshot"]["overdue_count"] == 1
    assert snapshot_response["progress_snapshot"]["total_backlog_items"] == 1
    assert snapshot_response["saved"]["status"] == "success"
    assert snapshots_response["snapshot_count"] == 1
    assert "governance_portfolio_summary" in summary_response
    ProgressSnapshotRequest,
