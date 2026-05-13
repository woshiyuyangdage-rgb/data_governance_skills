"""Execution trace model for local tool-layer audit records."""

from pydantic import BaseModel, Field


class ExecutionTrace(BaseModel):
    """Summarized local audit record for one tool call."""

    trace_id: str
    session_id: str | None = None
    tool_name: str
    profile_name: str | None = None
    asset_name: str | None = None
    operation: str | None = None
    validation_status: str | None = None
    raw_text: str | None = None
    input_summary: dict[str, object] = Field(default_factory=dict)
    resolved_context_summary: dict[str, object] = Field(default_factory=dict)
    stages_executed: list[str] = Field(default_factory=list)
    status: str
    message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exported_files: dict[str, str] = Field(default_factory=dict)
    review_summary: dict[str, object] = Field(default_factory=dict)
    export_format: str | None = None
    exported_rule_count: int | None = None
    confirmed_rule_count: int | None = None
    package_id: str | None = None
    package_rule_count: int | None = None
    exported_package_path: str | None = None
    field_rule_count: int | None = None
    cross_field_rule_count: int | None = None
    low_confidence_rule_count: int | None = None
    review_queue_summary: dict[str, object] = Field(default_factory=dict)
    readiness_score_count: int | None = None
    gap_count: int | None = None
    remediation_action_count: int | None = None
    work_package_name: str | None = None
    backlog_item_count: int | None = None
    backlog_status_summary: dict[str, object] = Field(default_factory=dict)
    updated_backlog_id: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    overdue_count: int | None = None
    blocked_count: int | None = None
    owner_workload_summary: dict[str, object] = Field(default_factory=dict)
    snapshot_id: str | None = None
    workbook_count: int | None = None
    delivery_package_name: str | None = None
    delivery_output_dir: str | None = None
    generated_file_count: int | None = None
    batch_name: str | None = None
    file_count: int | None = None
    group_count: int | None = None
    changed_count: int | None = None
    new_count: int | None = None
    unchanged_count: int | None = None
    removed_count: int | None = None
    rerun_object_count: int | None = None
    workbook_type: str | None = None
    imported_count: int | None = None
    invalid_count: int | None = None
    changed_object_count: int | None = None
    rerun_changed_only: bool | None = None
    domain_pack_name: str | None = None
    template_name: str | None = None
    domain_pack_match_confidence: float | None = None
    applied_delivery_outputs: list[str] = Field(default_factory=list)
    intake_profile_name: str | None = None
    intake_match_confidence: float | None = None
    matched_sheet_name: str | None = None
    unmapped_source_column_count: int | None = None
    normalization_row_count: int | None = None
    confirmation_template_name: str | None = None
    template_match_confidence: float | None = None
    notes: list[str] = Field(default_factory=list)
