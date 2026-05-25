"""Cached UI helpers for Streamlit workbench pages."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, TypeVar

import streamlit as st

from app.core.adapters.manifest_service import (
    get_capability_manifest,
    get_mcp_style_manifest,
    get_native_tool_schemas,
    get_openai_tool_schemas,
)
from app.core.adapters.adapter_loader import load_adapter_config
from app.core.delivery.confirmation_workbook_importer import (
    ConfirmationWorkbookImporter,
)
from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.intake.intake_adapter_service import IntakeAdapterService
from app.core.models.capability_manifest import CapabilityManifest
from app.core.models.ai_ready_score import AiReadyScore
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.backlog_summary import BacklogSummary
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.domain_pack_match_result import DomainPackMatchResult
from app.core.models.execution_package_export_result import (
    ExecutionPackageExportResult,
)
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_portfolio_summary import GovernancePortfolioSummary
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult, UnmappedField
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.progress_snapshot import ProgressSnapshot
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.models.review_summary import ReviewSummary
from app.core.models.rule_export_result import RuleExportResult
from app.core.models.exported_tool_schema import ExportedToolSchema
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.models.stg_table_suggestion import StgTableSuggestion
from app.core.models.tool_definition import ToolDefinition
from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.intake_match_result import IntakeMatchResult
from app.core.models.intake_normalization_result import IntakeNormalizationResult
from app.core.parser.loader import load_metadata_file
from app.core.review.override_store import (
    load_mapping_overrides,
    load_stg_overrides,
)
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.tools.tool_service import list_tools
from app.core.tools.tool_loader import load_tool_registry
from app.core.utils.result_utils import (
    ai_ready_scores_to_dataframe as core_ai_ready_scores_to_dataframe,
    backlog_sla_statuses_to_dataframe as core_backlog_sla_statuses_to_dataframe,
    backlog_summary_to_dataframe as core_backlog_summary_to_dataframe,
    confirmed_quality_rules_to_dataframe as core_confirmed_quality_rules_to_dataframe,
    cross_field_quality_rules_to_dataframe as core_cross_field_quality_rules_to_dataframe,
    execution_package_export_results_to_dataframe as core_execution_package_export_results_to_dataframe,
    execution_package_summary_to_dataframe as core_execution_package_summary_to_dataframe,
    execution_ready_rules_to_dataframe as core_execution_ready_rules_to_dataframe,
    governance_backlog_items_to_dataframe as core_governance_backlog_items_to_dataframe,
    governance_gaps_to_dataframe as core_governance_gaps_to_dataframe,
    governance_portfolio_summary_to_dataframe as core_governance_portfolio_summary_to_dataframe,
    governance_work_package_summary_to_dataframe as core_governance_work_package_summary_to_dataframe,
    issues_to_dataframe as core_issues_to_dataframe,
    mapping_results_to_dataframe as core_mapping_results_to_dataframe,
    progress_snapshot_to_dataframe as core_progress_snapshot_to_dataframe,
    quality_rule_packages_to_dataframe as core_quality_rule_packages_to_dataframe,
    quality_rule_review_summary_to_dataframe as core_quality_rule_review_summary_to_dataframe,
    quality_review_queue_summary_to_dataframe as core_quality_review_queue_summary_to_dataframe,
    quality_rules_to_dataframe as core_quality_rules_to_dataframe,
    readiness_scores_to_dataframe as core_readiness_scores_to_dataframe,
    remediation_actions_to_dataframe as core_remediation_actions_to_dataframe,
    review_summary_to_dataframe as core_review_summary_to_dataframe,
    rule_export_results_to_dataframe as core_rule_export_results_to_dataframe,
    skill_outputs_to_dataframe as core_skill_outputs_to_dataframe,
    stg_fields_to_dataframe as core_stg_fields_to_dataframe,
    stg_tables_to_dataframe as core_stg_tables_to_dataframe,
    tasks_to_dataframe as core_tasks_to_dataframe,
    unmapped_fields_to_dataframe as core_unmapped_fields_to_dataframe,
)

T = TypeVar("T")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "app" / "config"
ADAPTER_LAYER_CONFIG_PATH = CONFIG_DIR / "adapter_layer.yaml"
TOOL_REGISTRY_CONFIG_PATH = CONFIG_DIR / "tool_registry.yaml"


def _cache_builder(builder: Callable[..., T]) -> Callable[..., T]:
    @st.cache_data(show_spinner=False)
    def cached(*args: Any, **kwargs: Any) -> T:
        return builder(*args, **kwargs)

    cached.__name__ = builder.__name__
    cached.__doc__ = builder.__doc__
    return cached


def file_cache_key(file_path: str | None) -> str:
    """Return a lightweight cache key for one file path."""
    if not file_path:
        return ""

    path = Path(file_path)
    try:
        stat = path.stat()
    except FileNotFoundError:
        return str(path)
    return f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"


def content_signature(content: bytes) -> str:
    """Return the stable md5 signature used for uploaded file identity."""
    return hashlib.md5(content).hexdigest()


def _read_file_bytes(file_path: str, cache_token: str | None = None) -> bytes:
    return Path(file_path).read_bytes()


def _read_csv_dataframe(file_path: str, cache_token: str | None = None) -> pd.DataFrame:
    return pd.read_csv(file_path)


def tool_registry_cache_key() -> str:
    """Return a cache token for the tool registry config file."""
    return file_cache_key(str(TOOL_REGISTRY_CONFIG_PATH))


def adapter_schema_cache_key() -> str:
    """Return a cache token for adapter-layer schema exports."""
    return "::".join(
        [
            file_cache_key(str(ADAPTER_LAYER_CONFIG_PATH)),
            tool_registry_cache_key(),
        ]
    )


def workflow_result_payload(
    workflow_result: WorkflowResult | dict[str, object] | None,
) -> dict[str, object]:
    """Return one JSON-safe workflow result payload for UI defaults."""
    if workflow_result is None:
        return {}
    if isinstance(workflow_result, dict):
        return workflow_result
    if hasattr(workflow_result, "model_dump"):
        return workflow_result.model_dump()
    return {}


def build_tool_console_default_arguments(
    uploaded_file_path: str | None,
    workflow_result: WorkflowResult | dict[str, object] | None,
    session_id: str,
) -> dict[str, dict[str, object]]:
    """Build default tool console request payloads."""
    workflow_result_payload_value = workflow_result_payload(workflow_result)
    return {
        "run_governance_profile": {
            "file_path": uploaded_file_path or "",
            "profile_name": "metadata_diagnosis_only",
            "export_reports": False,
            "apply_review_replay": False,
        },
        "recommend_quality_rules": {
            "file_path": uploaded_file_path or "",
            "profile_name": "diagnosis_mapping_stg_quality",
            "export_reports": False,
            "apply_review_replay": False,
        },
        "recommend_quality_intelligence": {
            "file_path": uploaded_file_path or "",
            "profile_name": "diagnosis_mapping_stg_quality",
            "export_reports": False,
            "apply_review_replay": False,
        },
        "review_quality_rules": {
            "workflow_result": workflow_result_payload_value,
            "review_inputs": {},
            "save_overrides": False,
        },
        "batch_review_quality_rules": {
            "workflow_result": workflow_result_payload_value,
            "action": "mark_low_confidence_manual_review",
            "confidence_threshold": 0.4,
            "save_overrides": False,
        },
        "export_confirmed_quality_rules": {
            "export_format": "json",
            "workflow_result": workflow_result_payload_value,
            "output_dir": str(PROJECT_ROOT / "outputs" / "rule_exports"),
            "base_filename": "tool_console_quality_rules",
            "apply_review_replay": True,
        },
        "build_execution_ready_package": {
            "workflow_result": workflow_result_payload_value,
            "file_path": uploaded_file_path or "",
            "apply_review_replay": True,
            "profile_name": "diagnosis_mapping_stg_quality_package_with_review",
        },
        "export_execution_ready_package": {
            "export_format": "manifest",
            "workflow_result": workflow_result_payload_value,
            "file_path": uploaded_file_path or "",
            "output_dir": str(PROJECT_ROOT / "outputs" / "execution_packages"),
            "base_filename": "tool_console_execution_package",
            "apply_review_replay": True,
        },
        "assess_rag_quality": {
            "documents": [],
            "chunks": [],
            "retrieval_logs": [],
            "answer_evaluations": [],
        },
        "assess_governance_readiness": {
            "workflow_result": workflow_result_payload_value,
            "file_path": uploaded_file_path or "",
            "apply_review_replay": True,
        },
        "build_governance_work_package": {
            "workflow_result": workflow_result_payload_value,
            "file_path": uploaded_file_path or "",
            "export_package": True,
            "output_dir": str(PROJECT_ROOT / "outputs" / "governance_work_packages"),
            "base_filename": "tool_console_governance_work_package",
            "apply_review_replay": True,
        },
        "interpret_governance_intent": {
            "text": "Run standard mapping and export reports",
            "file_path": uploaded_file_path or "",
        },
        "preview_agent_plan": {
            "text": "Help me inspect this file",
            "file_path": "",
            "session_id": session_id,
        },
        "run_agent_task": {
            "text": "Help me inspect this file",
            "file_path": "",
            "session_id": session_id,
            "force_run": False,
        },
        "resolve_governance_context": {
            "text": "Help me inspect this file",
            "file_path": "",
            "session_id": session_id,
        },
        "export_governance_reports": {
            "profile_name": "metadata_diagnosis_only",
            "result": workflow_result_payload_value,
            "output_dir": str(PROJECT_ROOT / "outputs" / "reports"),
            "base_filename": "tool_console_export",
        },
        "list_config_assets": {},
        "get_config_asset": {
            "asset_name": "workflow_profiles",
        },
        "validate_config_asset": {
            "asset_name": "workflow_profiles",
        },
        "save_config_asset": {
            "asset_name": "workflow_profiles",
            "content": (
                "profiles:\n"
                "  - name: metadata_diagnosis_only\n"
                "    enabled: true\n"
                "    description: Run metadata diagnosis only\n"
                "    stages:\n"
                "      - diagnosis\n"
                "    supports_review_replay: false\n"
                "    default_report_mode: diagnosis\n"
            ),
        },
        "publish_config_asset": {
            "asset_name": "workflow_profiles",
        },
    }


def build_adapter_console_default_arguments(
    uploaded_file_path: str | None,
    workflow_result: WorkflowResult | dict[str, object] | None,
) -> dict[str, dict[str, object]]:
    """Build default adapter console request payloads."""
    workflow_result_payload_value = workflow_result_payload(workflow_result)
    return {
        "run_governance_profile": {
            "file_path": uploaded_file_path or "",
            "profile_name": "metadata_diagnosis_only",
        },
        "validate_config_asset": {"asset_name": "workflow_profiles"},
        "list_config_assets": {},
        "run_agent_task": {
            "text": "Help me inspect this file",
            "file_path": uploaded_file_path or "",
            "force_run": True,
        },
        "review_quality_rules": {
            "workflow_result": workflow_result_payload_value,
            "review_inputs": {},
            "save_overrides": False,
        },
        "recommend_quality_intelligence": {
            "file_path": uploaded_file_path or "",
            "profile_name": "diagnosis_mapping_stg_quality",
            "apply_review_replay": False,
        },
        "batch_review_quality_rules": {
            "workflow_result": workflow_result_payload_value,
            "action": "mark_low_confidence_manual_review",
            "confidence_threshold": 0.4,
            "save_overrides": False,
        },
        "export_confirmed_quality_rules": {
            "export_format": "json",
            "workflow_result": workflow_result_payload_value,
            "output_dir": str(PROJECT_ROOT / "outputs" / "rule_exports"),
            "base_filename": "adapter_console_quality_rules",
            "apply_review_replay": True,
        },
        "build_execution_ready_package": {
            "workflow_result": workflow_result_payload_value,
            "file_path": uploaded_file_path or "",
            "apply_review_replay": True,
            "profile_name": "diagnosis_mapping_stg_quality_package_with_review",
        },
        "export_execution_ready_package": {
            "export_format": "manifest",
            "workflow_result": workflow_result_payload_value,
            "file_path": uploaded_file_path or "",
            "output_dir": str(PROJECT_ROOT / "outputs" / "execution_packages"),
            "base_filename": "adapter_console_execution_package",
            "apply_review_replay": True,
        },
        "assess_rag_quality": {
            "documents": [],
            "chunks": [],
            "retrieval_logs": [],
            "answer_evaluations": [],
        },
    }


def _refresh_tool_registry_cache() -> None:
    """Clear the local tool registry cache before a cached read."""
    load_tool_registry.cache_clear()


def _refresh_adapter_schema_cache() -> None:
    """Clear adapter schema caches before a cached read."""
    load_adapter_config.cache_clear()
    load_tool_registry.cache_clear()


issues_to_dataframe = _cache_builder(core_issues_to_dataframe)
tasks_to_dataframe = _cache_builder(core_tasks_to_dataframe)
skill_outputs_to_dataframe = _cache_builder(core_skill_outputs_to_dataframe)
mapping_results_to_dataframe = _cache_builder(core_mapping_results_to_dataframe)
unmapped_fields_to_dataframe = _cache_builder(core_unmapped_fields_to_dataframe)
stg_tables_to_dataframe = _cache_builder(core_stg_tables_to_dataframe)
stg_fields_to_dataframe = _cache_builder(core_stg_fields_to_dataframe)
quality_rules_to_dataframe = _cache_builder(core_quality_rules_to_dataframe)
quality_rule_packages_to_dataframe = _cache_builder(
    core_quality_rule_packages_to_dataframe
)
confirmed_quality_rules_to_dataframe = _cache_builder(
    core_confirmed_quality_rules_to_dataframe
)
cross_field_quality_rules_to_dataframe = _cache_builder(
    core_cross_field_quality_rules_to_dataframe
)
quality_rule_review_summary_to_dataframe = _cache_builder(
    core_quality_rule_review_summary_to_dataframe
)
quality_review_queue_summary_to_dataframe = _cache_builder(
    core_quality_review_queue_summary_to_dataframe
)
rule_export_results_to_dataframe = _cache_builder(core_rule_export_results_to_dataframe)
execution_ready_rules_to_dataframe = _cache_builder(core_execution_ready_rules_to_dataframe)
execution_package_summary_to_dataframe = _cache_builder(
    core_execution_package_summary_to_dataframe
)
execution_package_export_results_to_dataframe = _cache_builder(
    core_execution_package_export_results_to_dataframe
)
readiness_scores_to_dataframe = _cache_builder(core_readiness_scores_to_dataframe)
ai_ready_scores_to_dataframe = _cache_builder(core_ai_ready_scores_to_dataframe)
governance_gaps_to_dataframe = _cache_builder(core_governance_gaps_to_dataframe)
remediation_actions_to_dataframe = _cache_builder(core_remediation_actions_to_dataframe)
governance_work_package_summary_to_dataframe = _cache_builder(
    core_governance_work_package_summary_to_dataframe
)
governance_backlog_items_to_dataframe = _cache_builder(
    core_governance_backlog_items_to_dataframe
)
backlog_summary_to_dataframe = _cache_builder(core_backlog_summary_to_dataframe)
backlog_sla_statuses_to_dataframe = _cache_builder(core_backlog_sla_statuses_to_dataframe)
governance_portfolio_summary_to_dataframe = _cache_builder(
    core_governance_portfolio_summary_to_dataframe
)
progress_snapshot_to_dataframe = _cache_builder(core_progress_snapshot_to_dataframe)
review_summary_to_dataframe = _cache_builder(core_review_summary_to_dataframe)


def _load_metadata_file(file_path: str, file_signature: str | None = None) -> list[TableMeta]:
    return load_metadata_file(file_path)


def _match_domain_pack_from_file(
    file_path: str,
    file_signature: str | None = None,
) -> DomainPackMatchResult:
    tables = load_metadata_file(file_path)
    return DomainPackMatcher().match_domain_pack_from_tables(tables)


def _diagnose_intake_template(
    file_path: str,
    sheet_name: str | None = None,
    file_signature: str | None = None,
) -> IntakeMatchResult:
    return IntakeAdapterService().diagnose_intake_template(file_path, sheet_name=sheet_name)


def _normalize_metadata_input(
    file_path: str,
    profile_name: str | None = None,
    sheet_name: str | None = None,
    file_signature: str | None = None,
) -> IntakeNormalizationResult:
    return IntakeAdapterService().normalize_metadata_input(
        file_path,
        profile_name=profile_name,
        sheet_name=sheet_name,
    )


def _validate_confirmation_workbook(
    file_path: str,
    workbook_type: str,
    file_signature: str | None = None,
) -> Any:
    return ConfirmationWorkbookImporter().validate_workbook(file_path, workbook_type)


def _diagnose_confirmation_template(
    file_path: str,
    workbook_type: str,
    file_signature: str | None = None,
) -> ConfirmationTemplateMatchResult:
    return ConfirmationWorkbookImporter().diagnose_confirmation_template(
        file_path,
        workbook_type,
    )


def _load_mapping_overrides(cache_token: str | None = None) -> list[MappingReviewRecord]:
    return load_mapping_overrides()


def _load_stg_overrides(cache_token: str | None = None) -> list[StgReviewRecord]:
    return load_stg_overrides()


def _load_quality_rule_overrides(
    cache_token: str | None = None,
) -> list[QualityRuleReviewRecord]:
    return load_quality_rule_overrides()


load_metadata_file_cached = _cache_builder(_load_metadata_file)
read_file_bytes_cached = _cache_builder(_read_file_bytes)
read_csv_dataframe_cached = _cache_builder(_read_csv_dataframe)


def _list_tools(cache_token: str | None = None) -> list[ToolDefinition]:
    _refresh_tool_registry_cache()
    return list_tools()


def _get_capability_manifest(
    cache_token: str | None = None,
) -> CapabilityManifest:
    _refresh_adapter_schema_cache()
    return get_capability_manifest()


def _get_native_tool_schemas(
    cache_token: str | None = None,
) -> list[ExportedToolSchema]:
    _refresh_adapter_schema_cache()
    return get_native_tool_schemas()


def _get_openai_tool_schemas(
    cache_token: str | None = None,
) -> list[dict[str, object]]:
    _refresh_adapter_schema_cache()
    return get_openai_tool_schemas()


def _get_mcp_style_manifest(
    cache_token: str | None = None,
) -> dict[str, object]:
    _refresh_adapter_schema_cache()
    return get_mcp_style_manifest()


def _get_adapter_schema_bundle(
    cache_token: str | None = None,
) -> dict[str, object]:
    _refresh_adapter_schema_cache()
    return {
        "manifest": get_capability_manifest(),
        "native_schemas": get_native_tool_schemas(),
        "openai_schemas": get_openai_tool_schemas(),
        "mcp_manifest": get_mcp_style_manifest(),
    }


list_tools_cached = _cache_builder(_list_tools)
get_capability_manifest_cached = _cache_builder(_get_capability_manifest)
get_native_tool_schemas_cached = _cache_builder(_get_native_tool_schemas)
get_openai_tool_schemas_cached = _cache_builder(_get_openai_tool_schemas)
get_mcp_style_manifest_cached = _cache_builder(_get_mcp_style_manifest)
adapter_schema_bundle_cached = _cache_builder(_get_adapter_schema_bundle)
match_domain_pack_from_file_cached = _cache_builder(_match_domain_pack_from_file)
diagnose_intake_template_cached = _cache_builder(_diagnose_intake_template)
normalize_metadata_input_cached = _cache_builder(_normalize_metadata_input)
validate_confirmation_workbook_cached = _cache_builder(_validate_confirmation_workbook)
diagnose_confirmation_template_cached = _cache_builder(
    _diagnose_confirmation_template
)


load_mapping_overrides_cached = _cache_builder(_load_mapping_overrides)
load_stg_overrides_cached = _cache_builder(_load_stg_overrides)
load_quality_rule_overrides_cached = _cache_builder(_load_quality_rule_overrides)


def clear_review_override_caches() -> None:
    """Clear cached review override loads after a save."""
    load_mapping_overrides_cached.clear()
    load_stg_overrides_cached.clear()
    load_quality_rule_overrides_cached.clear()
