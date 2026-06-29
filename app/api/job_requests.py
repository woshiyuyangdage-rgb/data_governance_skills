"""Request models for governance job routes."""

from app.api.job_requests_backlog import (
    GovernanceBacklogBuildRequest,
    GovernanceBacklogStatusUpdateRequest,
    GovernancePortfolioAssessmentRequest,
    ProgressSnapshotRequest,
)
from app.api.job_requests_control_plane import (
    ConfigAssetSaveRequest,
    LearningMaintenanceReportExportRequest,
    LearningMemoryClearRequest,
    LearningMemoryRestoreRequest,
    ReviewLearningRebuildRequest,
)
from app.api.job_requests_core import (
    FileRunRequest,
    IntentTextRequest,
    ManualMetadataRequest,
    ManualMetadataRunRequest,
    MetadataMemoryLearningRequest,
)
from app.api.job_requests_delivery import (
    BatchGovernanceRequest,
    BatchSnapshotCompareRequest,
    ConfirmationWorkbookImportRequest,
    GovernanceDeliveryPackageRequest,
    GovernanceReadinessAssessmentRequest,
    GovernanceWorkPackageBuildRequest,
)
from app.api.job_requests_intake import (
    ConfirmationTemplateRequest,
    DomainPackMatchRequest,
    MetadataIntakeRequest,
    ProjectTemplateRunRequest,
)
from app.api.job_requests_project import (
    ProjectWorkspaceArtifactRequest,
    ProjectWorkspaceCreateRequest,
    ProjectWorkspaceReviewStateRequest,
    ProjectWorkspaceRunRecordRequest,
)
from app.api.job_requests_quality import (
    ConfirmedQualityRuleExportRequest,
    ExecutionPackageBuildRequest,
    ExecutionPackageExportRequest,
    MappingReviewSaveRequest,
    QualityRuleReviewRequest,
    StgReviewSaveRequest,
)
from app.api.job_requests_rag import RagQualityAssessmentRequest
from app.api.job_requests_text_to_sql import TextToSqlReadinessAssessmentRequest
from app.api.job_requests_tools import (
    AgentShellPlanRequest,
    AgentShellRunRequest,
    NativeToolInvokeRequest,
    OpenAIToolInvokeRequest,
)

__all__ = [
    "AgentShellPlanRequest",
    "AgentShellRunRequest",
    "BatchGovernanceRequest",
    "BatchSnapshotCompareRequest",
    "ConfigAssetSaveRequest",
    "ConfirmationTemplateRequest",
    "ConfirmationWorkbookImportRequest",
    "ConfirmedQualityRuleExportRequest",
    "DomainPackMatchRequest",
    "ExecutionPackageBuildRequest",
    "ExecutionPackageExportRequest",
    "FileRunRequest",
    "GovernanceBacklogBuildRequest",
    "GovernanceBacklogStatusUpdateRequest",
    "GovernanceDeliveryPackageRequest",
    "GovernancePortfolioAssessmentRequest",
    "GovernanceReadinessAssessmentRequest",
    "GovernanceWorkPackageBuildRequest",
    "IntentTextRequest",
    "LearningMaintenanceReportExportRequest",
    "LearningMemoryClearRequest",
    "LearningMemoryRestoreRequest",
    "ManualMetadataRequest",
    "ManualMetadataRunRequest",
    "MappingReviewSaveRequest",
    "MetadataIntakeRequest",
    "MetadataMemoryLearningRequest",
    "NativeToolInvokeRequest",
    "OpenAIToolInvokeRequest",
    "ProgressSnapshotRequest",
    "ProjectWorkspaceArtifactRequest",
    "ProjectWorkspaceCreateRequest",
    "ProjectWorkspaceReviewStateRequest",
    "ProjectWorkspaceRunRecordRequest",
    "ProjectTemplateRunRequest",
    "QualityRuleReviewRequest",
    "RagQualityAssessmentRequest",
    "ReviewLearningRebuildRequest",
    "StgReviewSaveRequest",
    "TextToSqlReadinessAssessmentRequest",
]
