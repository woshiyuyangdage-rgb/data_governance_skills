"""Models for platform-wide local data metrics."""

from pydantic import BaseModel, Field


class PlatformKpi(BaseModel):
    """Top-level platform metric."""

    name: str
    value: int | float | str
    description: str | None = None


class PlatformDistributionItem(BaseModel):
    """One count in a platform distribution."""

    name: str
    count: int


class PlatformWorkspaceMetric(BaseModel):
    """Dashboard row for one governance project workspace."""

    workspace_id: str
    name: str
    status: str
    owner_role: str | None = None
    run_count: int = 0
    artifact_count: int = 0
    pending_review_count: int = 0
    delivery_completeness_score: int = 0
    delivery_completeness_level: str = "not_started"
    missing_delivery_components: list[str] = Field(default_factory=list)
    last_run_status: str | None = None
    updated_at: str | None = None


class PlatformRecentActivity(BaseModel):
    """One recent local platform activity."""

    activity_type: str
    label: str
    status: str | None = None
    occurred_at: str | None = None
    source_id: str | None = None


class PlatformFileInventoryItem(BaseModel):
    """One local file inventory bucket."""

    bucket: str
    file_count: int = 0
    total_bytes: int = 0


class PlatformHealthSignal(BaseModel):
    """One platform health or risk signal."""

    severity: str
    signal_type: str
    title: str
    detail: str
    count: int | float = 0
    recommended_action: str | None = None


class PlatformMetrics(BaseModel):
    """Aggregated local platform metrics for the Streamlit dashboard."""

    generated_at: str
    kpis: list[PlatformKpi] = Field(default_factory=list)
    workspace_metrics: list[PlatformWorkspaceMetric] = Field(default_factory=list)
    workspace_status_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    run_status_distribution: list[PlatformDistributionItem] = Field(default_factory=list)
    workflow_profile_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    artifact_type_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    backlog_status_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    backlog_priority_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    backlog_owner_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    trace_status_distribution: list[PlatformDistributionItem] = Field(
        default_factory=list
    )
    trace_tool_distribution: list[PlatformDistributionItem] = Field(default_factory=list)
    output_inventory: list[PlatformFileInventoryItem] = Field(default_factory=list)
    recent_activities: list[PlatformRecentActivity] = Field(default_factory=list)
    health_signals: list[PlatformHealthSignal] = Field(default_factory=list)
