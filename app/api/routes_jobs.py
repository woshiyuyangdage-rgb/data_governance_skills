"""Aggregated routes for governance job execution.

This module keeps the historical `app.api.routes_jobs` import surface while the
route implementations live in smaller domain-focused modules.
"""

from fastapi import APIRouter
from app.api.job_requests import (
    AgentShellPlanRequest,
    AgentShellRunRequest,
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
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
    ProgressSnapshotRequest,
    QualityRuleReviewRequest,
    RagQualityAssessmentRequest,
)
from app.api.routes_jobs_backlog import (
    assess_governance_portfolio_route,
    build_governance_backlog_route,
    generate_progress_snapshot_route,
    governance_backlog_route,
    governance_backlog_summary_route,
    governance_portfolio_summary_route,
    governance_progress_snapshots_route,
    router as backlog_router,
    update_governance_backlog_status_route,
)
from app.api.routes_jobs_core import (
    interpret_governance_task,
    list_jobs,
    list_workflow_profiles,
    router as core_router,
    run_governance_task_route,
    run_interpreted_governance_task,
)
from app.api.routes_jobs_control_plane import (
    get_config_asset_route,
    list_config_assets_route,
    publish_config_asset_route,
    router as control_plane_router,
    save_config_asset_route,
    validate_config_asset_route,
)
from app.api.routes_jobs_delivery import (
    assess_governance_readiness_route,
    build_governance_work_package_route,
    governance_readiness_summary_route,
    router as delivery_router,
)
from app.api.routes_jobs_intake import router as intake_router
from app.api.routes_jobs_quality import (
    build_execution_ready_package_route,
    execution_package_summary_route,
    export_confirmed_quality_rules_route,
    export_execution_ready_package_route,
    quality_rule_review_summary_route,
    review_quality_rules_route,
    router as quality_router,
)
from app.api.routes_jobs_rag import (
    assess_rag_quality_route,
    router as rag_router,
)
from app.api.routes_jobs_tools import (
    agent_shell_plan,
    agent_shell_resolve_context,
    agent_shell_run,
    agent_shell_session,
    capability_manifest_route,
    call_tool_route,
    get_trace_route,
    invoke_native_tool_route,
    invoke_openai_tool_route,
    list_recent_traces_route,
    list_tools_route,
    mcp_tool_manifest_route,
    native_tool_schemas_route,
    openai_tool_schemas_route,
    router as tools_router,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
router.include_router(intake_router)
router.include_router(core_router)
router.include_router(tools_router)
router.include_router(control_plane_router)
router.include_router(quality_router)
router.include_router(rag_router)
router.include_router(delivery_router)
router.include_router(backlog_router)

__all__ = [
    "AgentShellPlanRequest",
    "AgentShellRunRequest",
    "ConfigAssetSaveRequest",
    "ConfirmedQualityRuleExportRequest",
    "ExecutionPackageBuildRequest",
    "ExecutionPackageExportRequest",
    "GovernanceBacklogBuildRequest",
    "GovernanceBacklogStatusUpdateRequest",
    "GovernancePortfolioAssessmentRequest",
    "GovernanceReadinessAssessmentRequest",
    "GovernanceWorkPackageBuildRequest",
    "IntentTextRequest",
    "NativeToolInvokeRequest",
    "OpenAIToolInvokeRequest",
    "ProgressSnapshotRequest",
    "QualityRuleReviewRequest",
    "RagQualityAssessmentRequest",
    "agent_shell_plan",
    "agent_shell_resolve_context",
    "agent_shell_run",
    "agent_shell_session",
    "assess_governance_portfolio_route",
    "assess_governance_readiness_route",
    "assess_rag_quality_route",
    "build_execution_ready_package_route",
    "build_governance_backlog_route",
    "build_governance_work_package_route",
    "call_tool_route",
    "capability_manifest_route",
    "execution_package_summary_route",
    "export_confirmed_quality_rules_route",
    "export_execution_ready_package_route",
    "generate_progress_snapshot_route",
    "get_config_asset_route",
    "get_trace_route",
    "governance_backlog_route",
    "governance_backlog_summary_route",
    "governance_portfolio_summary_route",
    "governance_progress_snapshots_route",
    "governance_readiness_summary_route",
    "interpret_governance_task",
    "invoke_native_tool_route",
    "invoke_openai_tool_route",
    "list_config_assets_route",
    "list_jobs",
    "list_recent_traces_route",
    "list_tools_route",
    "list_workflow_profiles",
    "mcp_tool_manifest_route",
    "native_tool_schemas_route",
    "openai_tool_schemas_route",
    "publish_config_asset_route",
    "quality_rule_review_summary_route",
    "review_quality_rules_route",
    "router",
    "run_governance_task_route",
    "run_interpreted_governance_task",
    "save_config_asset_route",
    "update_governance_backlog_status_route",
    "validate_config_asset_route",
]
