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
    LearningMaintenanceReportExportRequest,
    LearningMemoryClearRequest,
    LearningMemoryRestoreRequest,
    ManualMetadataRequest,
    ManualMetadataRunRequest,
    MetadataMemoryLearningRequest,
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
    ProgressSnapshotRequest,
    ProjectWorkspaceArtifactRequest,
    ProjectWorkspaceCreateRequest,
    ProjectWorkspaceReviewStateRequest,
    ProjectWorkspaceRunRecordRequest,
    QualityRuleReviewRequest,
    RagQualityAssessmentRequest,
    ReviewLearningRebuildRequest,
    TextToSqlReadinessAssessmentRequest,
)
from app.api.routes_jobs_backlog import (
    assess_governance_portfolio_route,
    build_governance_backlog_route,
    generate_progress_snapshot_route,
    governance_backlog_route,
    governance_backlog_summary_route,
    governance_portfolio_summary_route,
    governance_progress_snapshots_route,
    update_governance_backlog_status_route,
)
from app.api.routes_jobs_backlog import (
    router as backlog_router,
)
from app.api.routes_jobs_control_plane import (
    backup_then_prune_invalid_learning_memory_route,
    clear_learning_memory_field_key_route,
    create_learning_memory_backup_route,
    export_learning_maintenance_report_route,
    get_config_asset_route,
    learning_health_details_route,
    learning_health_route,
    learning_maintenance_report_route,
    list_config_assets_route,
    list_learning_memory_backups_route,
    prune_invalid_learning_memory_route,
    publish_config_asset_route,
    rebuild_review_learning_route,
    restore_learning_memory_backup_route,
    save_config_asset_route,
    validate_config_asset_route,
    validate_learning_memory_backup_route,
)
from app.api.routes_jobs_control_plane import (
    router as control_plane_router,
)
from app.api.routes_jobs_core import (
    interpret_governance_task,
    learn_metadata_memory_from_file_route,
    list_jobs,
    list_workflow_profiles,
    run_governance_task_route,
    run_interpreted_governance_task,
    run_manual_metadata_route,
    save_manual_metadata_route,
)
from app.api.routes_jobs_core import (
    router as core_router,
)
from app.api.routes_jobs_delivery import (
    assess_governance_readiness_route,
    build_governance_work_package_route,
    governance_readiness_summary_route,
)
from app.api.routes_jobs_delivery import (
    router as delivery_router,
)
from app.api.routes_jobs_intake import router as intake_router
from app.api.routes_jobs_project import (
    attach_project_workspace_artifact_route,
    create_project_workspace_route,
    project_workspace_detail_route,
    project_workspaces_route,
    record_project_workspace_run_route,
    set_project_workspace_review_state_route,
)
from app.api.routes_jobs_project import (
    router as project_router,
)
from app.api.routes_jobs_quality import (
    build_execution_ready_package_route,
    execution_package_summary_route,
    export_confirmed_quality_rules_route,
    export_execution_ready_package_route,
    quality_rule_review_summary_route,
    review_quality_rules_route,
)
from app.api.routes_jobs_quality import (
    router as quality_router,
)
from app.api.routes_jobs_rag import (
    assess_rag_quality_route,
)
from app.api.routes_jobs_rag import (
    router as rag_router,
)
from app.api.routes_jobs_text_to_sql import (
    assess_text_to_sql_readiness_route,
)
from app.api.routes_jobs_text_to_sql import (
    router as text_to_sql_router,
)
from app.api.routes_jobs_tools import (
    agent_shell_plan,
    agent_shell_resolve_context,
    agent_shell_run,
    agent_shell_session,
    call_tool_route,
    capability_manifest_route,
    get_trace_route,
    invoke_native_tool_route,
    invoke_openai_tool_route,
    list_recent_traces_route,
    list_tools_route,
    mcp_tool_manifest_route,
    native_tool_schemas_route,
    openai_tool_schemas_route,
)
from app.api.routes_jobs_tools import (
    router as tools_router,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
router.include_router(intake_router)
router.include_router(core_router)
router.include_router(tools_router)
router.include_router(control_plane_router)
router.include_router(quality_router)
router.include_router(rag_router)
router.include_router(text_to_sql_router)
router.include_router(delivery_router)
router.include_router(backlog_router)
router.include_router(project_router)

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
    "LearningMaintenanceReportExportRequest",
    "LearningMemoryClearRequest",
    "LearningMemoryRestoreRequest",
    "ManualMetadataRequest",
    "ManualMetadataRunRequest",
    "MetadataMemoryLearningRequest",
    "NativeToolInvokeRequest",
    "OpenAIToolInvokeRequest",
    "ProgressSnapshotRequest",
    "ProjectWorkspaceArtifactRequest",
    "ProjectWorkspaceCreateRequest",
    "ProjectWorkspaceReviewStateRequest",
    "ProjectWorkspaceRunRecordRequest",
    "QualityRuleReviewRequest",
    "RagQualityAssessmentRequest",
    "ReviewLearningRebuildRequest",
    "TextToSqlReadinessAssessmentRequest",
    "agent_shell_plan",
    "agent_shell_resolve_context",
    "agent_shell_run",
    "agent_shell_session",
    "assess_governance_portfolio_route",
    "assess_governance_readiness_route",
    "assess_rag_quality_route",
    "assess_text_to_sql_readiness_route",
    "attach_project_workspace_artifact_route",
    "build_execution_ready_package_route",
    "build_governance_backlog_route",
    "build_governance_work_package_route",
    "call_tool_route",
    "capability_manifest_route",
    "backup_then_prune_invalid_learning_memory_route",
    "clear_learning_memory_field_key_route",
    "create_learning_memory_backup_route",
    "create_project_workspace_route",
    "execution_package_summary_route",
    "export_confirmed_quality_rules_route",
    "export_execution_ready_package_route",
    "export_learning_maintenance_report_route",
    "generate_progress_snapshot_route",
    "get_config_asset_route",
    "get_trace_route",
    "governance_backlog_route",
    "governance_backlog_summary_route",
    "governance_portfolio_summary_route",
    "governance_progress_snapshots_route",
    "governance_readiness_summary_route",
    "interpret_governance_task",
    "learn_metadata_memory_from_file_route",
    "invoke_native_tool_route",
    "invoke_openai_tool_route",
    "learning_health_details_route",
    "learning_health_route",
    "learning_maintenance_report_route",
    "list_config_assets_route",
    "list_learning_memory_backups_route",
    "list_jobs",
    "list_recent_traces_route",
    "list_tools_route",
    "list_workflow_profiles",
    "mcp_tool_manifest_route",
    "native_tool_schemas_route",
    "openai_tool_schemas_route",
    "project_workspace_detail_route",
    "project_workspaces_route",
    "publish_config_asset_route",
    "prune_invalid_learning_memory_route",
    "quality_rule_review_summary_route",
    "review_quality_rules_route",
    "rebuild_review_learning_route",
    "record_project_workspace_run_route",
    "router",
    "run_governance_task_route",
    "run_interpreted_governance_task",
    "run_manual_metadata_route",
    "save_config_asset_route",
    "save_manual_metadata_route",
    "set_project_workspace_review_state_route",
    "restore_learning_memory_backup_route",
    "update_governance_backlog_status_route",
    "validate_config_asset_route",
    "validate_learning_memory_backup_route",
]
