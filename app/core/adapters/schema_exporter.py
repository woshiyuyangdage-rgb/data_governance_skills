"""Export local governance tools into adapter-friendly schema formats."""

from app.core.adapters.adapter_loader import load_adapter_config
from app.core.models.capability_manifest import CapabilityManifest
from app.core.models.exported_tool_schema import ExportedToolSchema
from app.core.tools.tool_loader import load_tool_registry
from app.core.utils.time_utils import utc_now_seconds

MODEL_SCHEMA_MAP: dict[str, dict[str, object]] = {
    "GovernanceTaskRequest": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "file_paths": {"type": "array", "items": {"type": "string"}},
            "profile_name": {"type": "string"},
            "domain_pack_name": {"type": "string"},
            "template_name": {"type": "string"},
            "intake_profile_name": {"type": "string"},
            "auto_match_template": {"type": "boolean"},
            "sheet_name": {"type": "string"},
            "confirmation_template_name": {"type": "string"},
            "apply_review_replay": {"type": "boolean"},
            "export_reports": {"type": "boolean"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
        },
        "required": ["profile_name"],
    },
    "QualityRuleToolRequest": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "profile_name": {"type": "string"},
            "apply_review_replay": {"type": "boolean"},
            "export_reports": {"type": "boolean"},
            "preferred_result_mode": {"type": "string"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
        },
    },
    "GovernanceTaskResponse": {
        "type": "object",
        "properties": {
            "profile_name": {"type": "string"},
            "status": {"type": "string"},
            "message": {"type": "string"},
            "stages_executed": {"type": "array", "items": {"type": "string"}},
            "exported_files": {"type": "object"},
        },
    },
    "WorkflowResult": {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
            "input_table_count": {"type": "integer"},
            "issue_count": {"type": "integer"},
            "task_count": {"type": "integer"},
            "mapping_results": {"type": "array", "items": {"type": "object"}},
            "stg_field_suggestions": {"type": "array", "items": {"type": "object"}},
            "quality_rule_suggestions": {"type": "array", "items": {"type": "object"}},
            "cross_field_quality_rules": {"type": "array", "items": {"type": "object"}},
            "confirmed_quality_rules": {"type": "array", "items": {"type": "object"}},
            "quality_rule_review_summary": {"type": "object"},
            "quality_review_queue_summary": {"type": "object"},
            "rule_export_results": {"type": "array", "items": {"type": "object"}},
            "execution_ready_package": {"type": "object"},
            "execution_package_summary": {"type": "object"},
            "execution_package_export_results": {"type": "array", "items": {"type": "object"}},
            "readiness_scores": {"type": "array", "items": {"type": "object"}},
            "governance_gaps": {"type": "array", "items": {"type": "object"}},
            "remediation_actions": {"type": "array", "items": {"type": "object"}},
            "governance_work_package": {"type": "object"},
            "readiness_summary": {"type": "object"},
            "governance_backlog_items": {"type": "array", "items": {"type": "object"}},
            "backlog_summary": {"type": "object"},
            "backlog_sla_statuses": {"type": "array", "items": {"type": "object"}},
            "governance_portfolio_summary": {"type": "object"},
            "progress_snapshot": {"type": "object"},
            "quality_rule_summary": {"type": "string"},
            "domain_pack_match": {"type": "object"},
            "project_template_result": {"type": "object"},
            "intake_match_result": {"type": "object"},
            "intake_mapping_result": {"type": "object"},
            "intake_normalization_result": {"type": "object"},
            "confirmation_template_match_result": {"type": "object"},
            "confirmation_template_mapping_result": {"type": "object"},
        },
    },
    "EmptyArguments": {
        "type": "object",
        "properties": {},
    },
    "DomainPackMatchArguments": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["text"],
    },
    "DomainPackMatchResult": {
        "type": "object",
        "properties": {
            "matched_pack_name": {"type": "string"},
            "confidence": {"type": "number"},
            "matched_tokens": {"type": "array", "items": {"type": "string"}},
            "fallback_used": {"type": "boolean"},
            "message": {"type": "string"},
        },
    },
    "ProjectTemplateRunArguments": {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"},
            "file_path": {"type": "string"},
            "domain_pack_name": {"type": "string"},
            "output_dir": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["template_name", "file_path"],
    },
    "MetadataIntakeDiagnoseArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "sheet_name": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["file_path"],
    },
    "MetadataIntakeNormalizeArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "intake_profile_name": {"type": "string"},
            "sheet_name": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["file_path"],
    },
    "GovernanceWithIntakeArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "profile_name": {"type": "string"},
            "intake_profile_name": {"type": "string"},
            "sheet_name": {"type": "string"},
            "export_reports": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
        "required": ["file_path"],
    },
    "IntakeMatchResult": {
        "type": "object",
        "properties": {
            "matched_profile_name": {"type": "string"},
            "confidence": {"type": "number"},
            "matched_sheet_name": {"type": "string"},
            "matched_headers": {"type": "array", "items": {"type": "string"}},
            "missing_required_fields": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "fallback_used": {"type": "boolean"},
            "message": {"type": "string"},
        },
    },
    "IntakeNormalizationResult": {
        "type": "object",
        "properties": {
            "profile_name": {"type": "string"},
            "row_count": {"type": "integer"},
            "table_count": {"type": "integer"},
            "normalized_records": {"type": "array", "items": {"type": "object"}},
            "mapping_result": {"type": "object"},
            "status": {"type": "string"},
            "message": {"type": "string"},
        },
    },
    "ConfirmationTemplateDiagnoseArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workbook_type": {"type": "string"},
            "sheet_name": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["file_path"],
    },
    "ConfirmationTemplateImportArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "confirmation_template_name": {"type": "string"},
            "workbook_type": {"type": "string"},
            "sheet_name": {"type": "string"},
            "rerun_changed_only": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
        "required": ["file_path"],
    },
    "ConfirmationTemplateMatchResult": {
        "type": "object",
        "properties": {
            "matched_template_name": {"type": "string"},
            "workbook_type": {"type": "string"},
            "confidence": {"type": "number"},
            "matched_sheet_name": {"type": "string"},
            "matched_headers": {"type": "array", "items": {"type": "string"}},
            "missing_required_fields": {"type": "array", "items": {"type": "string"}},
            "unmapped_source_columns": {"type": "array", "items": {"type": "string"}},
            "fallback_used": {"type": "boolean"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "message": {"type": "string"},
        },
    },
    "QualityRuleReviewArguments": {
        "type": "object",
        "properties": {
            "quality_rule_suggestions": {"type": "array", "items": {"type": "object"}},
            "cross_field_quality_rules": {"type": "array", "items": {"type": "object"}},
            "workflow_result": {"type": "object"},
            "review_inputs": {"type": "object"},
            "records": {"type": "array", "items": {"type": "object"}},
            "save_overrides": {"type": "boolean"},
            "source": {"type": "string"},
        },
    },
    "QualityBatchReviewArguments": {
        "type": "object",
        "properties": {
            "quality_rule_suggestions": {"type": "array", "items": {"type": "object"}},
            "cross_field_quality_rules": {"type": "array", "items": {"type": "object"}},
            "workflow_result": {"type": "object"},
            "action": {
                "type": "string",
                "enum": [
                    "accept_by_rule_type",
                    "accept_by_table",
                    "mark_low_confidence_manual_review",
                ],
            },
            "rule_type": {"type": "string"},
            "table_name": {"type": "string"},
            "confidence_threshold": {"type": "number"},
            "save_overrides": {"type": "boolean"},
        },
    },
    "RuleExportArguments": {
        "type": "object",
        "properties": {
            "export_format": {"type": "string", "enum": ["json", "custom_json", "dbt", "dbt_yaml", "yaml", "both"]},
            "confirmed_quality_rules": {"type": "array", "items": {"type": "object"}},
            "workflow_result": {"type": "object"},
            "file_path": {"type": "string"},
            "apply_review_replay": {"type": "boolean"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
        },
    },
    "RuleExportResult": {
        "type": "object",
        "properties": {
            "export_format": {"type": "string"},
            "output_path": {"type": "string"},
            "rule_count": {"type": "integer"},
            "status": {"type": "string"},
            "message": {"type": "string"},
        },
    },
    "ExecutionPackageBuildArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "apply_review_replay": {"type": "boolean"},
            "profile_name": {"type": "string"},
            "confirmed_quality_rules": {"type": "array", "items": {"type": "object"}},
            "workflow_result": {"type": "object"},
            "execution_ready_package": {"type": "object"},
        },
    },
    "ExecutionPackageExportArguments": {
        "type": "object",
        "properties": {
            "export_format": {
                "type": "string",
                "enum": ["json", "package_json", "manifest", "package_manifest", "dbt", "dbt_yaml", "yaml", "all", "both"],
            },
            "file_path": {"type": "string"},
            "apply_review_replay": {"type": "boolean"},
            "confirmed_quality_rules": {"type": "array", "items": {"type": "object"}},
            "workflow_result": {"type": "object"},
            "execution_ready_package": {"type": "object"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
        },
    },
    "ExecutionPackageExportResult": {
        "type": "object",
        "properties": {
            "export_format": {"type": "string"},
            "output_path": {"type": "string"},
            "package_id": {"type": "string"},
            "rule_count": {"type": "integer"},
            "status": {"type": "string"},
            "message": {"type": "string"},
        },
    },
    "GovernanceReadinessAssessmentArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workflow_result": {"type": "object"},
            "apply_review_replay": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
    },
    "GovernanceWorkPackageArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workflow_result": {"type": "object"},
            "apply_review_replay": {"type": "boolean"},
            "package_name": {"type": "string"},
            "export_package": {"type": "boolean"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
            "session_id": {"type": "string"},
        },
    },
    "GovernanceBacklogBuildArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workflow_result": {"type": "object"},
            "remediation_actions": {"type": "array", "items": {"type": "object"}},
            "governance_backlog_items": {"type": "array", "items": {"type": "object"}},
            "apply_review_replay": {"type": "boolean"},
            "persist": {"type": "boolean"},
            "append": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
    },
    "GovernanceBacklogStatusUpdateArguments": {
        "type": "object",
        "properties": {
            "backlog_id": {"type": "string"},
            "new_status": {"type": "string"},
            "note": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["backlog_id", "new_status"],
    },
    "GovernanceBacklogListArguments": {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "priority": {"type": "string"},
            "owner_role": {"type": "string"},
            "gap_type": {"type": "string"},
            "overdue_only": {"type": "boolean"},
            "sla_status": {"type": "string"},
            "session_id": {"type": "string"},
        },
    },
    "GovernancePortfolioAssessmentArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workflow_result": {"type": "object"},
            "governance_backlog_items": {"type": "array", "items": {"type": "object"}},
            "backlog_sla_statuses": {"type": "array", "items": {"type": "object"}},
            "apply_review_replay": {"type": "boolean"},
            "notes": {"type": "string"},
            "session_id": {"type": "string"},
        },
    },
    "ProgressSnapshotArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workflow_result": {"type": "object"},
            "governance_backlog_items": {"type": "array", "items": {"type": "object"}},
            "backlog_sla_statuses": {"type": "array", "items": {"type": "object"}},
            "apply_review_replay": {"type": "boolean"},
            "notes": {"type": "string"},
            "save": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
    },
    "BacklogUpdateResult": {
        "type": "object",
        "properties": {
            "backlog_id": {"type": "string"},
            "old_status": {"type": "string"},
            "new_status": {"type": "string"},
            "status": {"type": "string"},
            "message": {"type": "string"},
            "updated_at": {"type": "string"},
        },
    },
    "IntentTextRequest": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "file_path": {"type": "string"},
        },
        "required": ["text"],
    },
    "IntentExecutionResult": {
        "type": "object",
        "properties": {
            "interpreted_intent": {"type": "object"},
            "task_request": {"type": "object"},
            "task_response": {"type": "object"},
        },
    },
    "AgentShellPlanRequest": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "file_path": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["text"],
    },
    "AgentShellRunRequest": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "file_path": {"type": "string"},
            "session_id": {"type": "string"},
            "force_run": {"type": "boolean"},
        },
        "required": ["text"],
    },
    "AgentShellResult": {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
            "session_id": {"type": "string"},
            "execution_plan": {"type": "object"},
            "resolved_context": {"type": "object"},
            "task_response": {"type": "object"},
        },
    },
    "ReportExportArguments": {
        "type": "object",
        "properties": {
            "profile_name": {"type": "string"},
            "result": {"type": "object"},
            "workflow_result": {"type": "object"},
            "task_response": {"type": "object"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
            "preferred_result_mode": {"type": "string"},
        },
    },
    "DeliveryPackageArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workflow_result": {"type": "object"},
            "apply_review_replay": {"type": "boolean"},
            "output_dir": {"type": "string"},
            "base_filename": {"type": "string"},
            "base_name": {"type": "string"},
            "session_id": {"type": "string"},
        },
    },
    "BatchGovernanceArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "file_paths": {"type": "array", "items": {"type": "string"}},
            "group_by": {
                "type": "string",
                "enum": ["system_name", "schema_name", "domain_hint"],
            },
            "batch_name": {"type": "string"},
            "base_filename": {"type": "string"},
            "session_id": {"type": "string"},
        },
    },
    "BatchSnapshotCompareArguments": {
        "type": "object",
        "properties": {
            "batch_name": {"type": "string"},
            "session_id": {"type": "string"},
        },
    },
    "WorkbookImportArguments": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "workbook_type": {
                "type": "string",
                "enum": [
                    "mapping_confirmation",
                    "stg_confirmation",
                    "quality_rule_confirmation",
                    "backlog_confirmation",
                ],
            },
            "rerun_changed_only": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
        "required": ["file_path", "workbook_type"],
    },
    "ConfigAssetLookupRequest": {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["asset_name"],
    },
    "ConfigAssetSaveRequest": {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string"},
            "content": {"type": "object"},
            "session_id": {"type": "string"},
        },
        "required": ["asset_name", "content"],
    },
    "ValidationResult": {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string"},
            "is_valid": {"type": "boolean"},
            "messages": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
    },
    "ConfigEditResult": {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string"},
            "status": {"type": "string"},
            "message": {"type": "string"},
            "backup_path": {"type": "string"},
            "validation_result": {"type": "object"},
        },
    },
    "dict": {"type": "object"},
    "list": {"type": "array", "items": {"type": "object"}},
}

TOOL_EXAMPLES: dict[str, list[dict[str, object]]] = {
    "run_governance_profile": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "profile_name": "metadata_diagnosis_only",
        }
    ],
    "recommend_quality_rules": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "profile_name": "diagnosis_mapping_stg_quality",
            "apply_review_replay": False,
        }
    ],
    "recommend_quality_intelligence": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "profile_name": "diagnosis_mapping_stg_quality",
            "apply_review_replay": False,
        }
    ],
    "review_quality_rules": [
        {
            "workflow_result": {"quality_rule_suggestions": []},
            "review_inputs": {},
            "save_overrides": False,
        }
    ],
    "batch_review_quality_rules": [
        {
            "workflow_result": {"quality_rule_suggestions": [], "cross_field_quality_rules": []},
            "action": "mark_low_confidence_manual_review",
            "confidence_threshold": 0.4,
            "save_overrides": False,
        }
    ],
    "export_confirmed_quality_rules": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
            "export_format": "json",
        }
    ],
    "build_execution_ready_package": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
            "profile_name": "diagnosis_mapping_stg_quality_package_with_review",
        }
    ],
    "export_execution_ready_package": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
            "export_format": "manifest",
        }
    ],
    "assess_governance_readiness": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
        }
    ],
    "build_governance_work_package": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "export_package": True,
            "base_filename": "governance_work_package_demo",
        }
    ],
    "build_governance_backlog": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "persist": False,
            "apply_review_replay": True,
        }
    ],
    "update_governance_backlog_status": [
        {
            "backlog_id": "backlog_example",
            "new_status": "accepted",
            "note": "Accepted for local tracking.",
        }
    ],
    "list_governance_backlog_items": [
        {
            "status": "proposed",
        }
    ],
    "assess_governance_portfolio": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
        }
    ],
    "generate_progress_snapshot": [
        {
            "governance_backlog_items": [],
            "backlog_sla_statuses": [],
            "save": False,
        }
    ],
    "list_governance_progress_snapshots": [{}],
    "export_confirmation_workbooks": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
            "base_filename": "confirmation_workbook_demo",
        }
    ],
    "build_governance_delivery_package": [
        {
            "file_path": "app/data/samples/sample_metadata.csv",
            "apply_review_replay": True,
            "base_filename": "governance_delivery_demo",
        }
    ],
    "run_batch_governance": [
        {
            "file_paths": ["app/data/samples/sample_metadata.csv"],
            "group_by": "system_name",
            "batch_name": "demo_batch",
        }
    ],
    "run_incremental_rerun": [
        {
            "file_paths": ["app/data/samples/sample_metadata.csv"],
            "group_by": "system_name",
            "batch_name": "demo_batch",
        }
    ],
    "compare_governance_snapshots": [{"batch_name": "demo_batch"}],
    "import_confirmation_workbook": [
        {
            "file_path": "outputs/delivery_packages/demo/mapping_confirmation_workbook.xlsx",
            "workbook_type": "mapping_confirmation",
        }
    ],
    "import_confirmation_and_rerun": [
        {
            "file_path": "outputs/delivery_packages/demo/mapping_confirmation_workbook.xlsx",
            "workbook_type": "mapping_confirmation",
            "rerun_changed_only": True,
        }
    ],
    "preview_agent_plan": [
        {"text": "Help me inspect this file", "session_id": "demo_session"}
    ],
    "run_agent_task": [
        {
            "text": "Run standard mapping and export reports",
            "file_path": "app/data/samples/sample_metadata.csv",
            "force_run": True,
        }
    ],
    "list_config_assets": [{}],
    "validate_config_asset": [{"asset_name": "workflow_profiles"}],
    "publish_config_asset": [{"asset_name": "tool_registry"}],
}


def _utc_now() -> str:
    return utc_now_seconds()


class SchemaExporter:
    """Export local tool definitions into adapter-ready schema formats."""

    def __init__(self) -> None:
        self.config = load_adapter_config()

    def _include_disabled_tools(self) -> bool:
        schema_export = self.config.get("schema_export", {})
        return bool(schema_export.get("include_disabled_tools", False))

    def _include_examples(self) -> bool:
        schema_export = self.config.get("schema_export", {})
        return bool(schema_export.get("include_examples", True))

    def _compatibility_enabled(self, key: str, default: bool = True) -> bool:
        compatibility = self.config.get("compatibility", {})
        return bool(compatibility.get(key, default))

    def _tool_definitions(self):
        definitions = load_tool_registry()
        if self._include_disabled_tools():
            return definitions
        return [definition for definition in definitions if definition.enabled]

    @staticmethod
    def _lookup_schema(model_name: str) -> dict[str, object]:
        return dict(MODEL_SCHEMA_MAP.get(model_name, {"type": "object"}))

    def _build_native_schema(self, definition) -> ExportedToolSchema:
        return ExportedToolSchema(
            tool_name=definition.name,
            description=definition.description,
            input_model=definition.input_model,
            output_model=definition.output_model,
            category=definition.category,
            input_schema=self._lookup_schema(definition.input_model),
            output_schema=self._lookup_schema(definition.output_model),
            examples=list(TOOL_EXAMPLES.get(definition.name, []))
            if self._include_examples()
            else [],
        )

    def export_native_tool_schemas(self) -> list[ExportedToolSchema]:
        """Return native tool schemas derived from the tool registry."""
        return [self._build_native_schema(definition) for definition in self._tool_definitions()]

    def export_openai_style_schemas(self) -> list[dict[str, object]]:
        """Return simplified OpenAI-style function schemas."""
        if not self._compatibility_enabled("export_openai_style_schema", True):
            return []
        schemas: list[dict[str, object]] = []
        for native_schema in self.export_native_tool_schemas():
            schema_payload: dict[str, object] = {
                "type": "function",
                "function": {
                    "name": native_schema.tool_name,
                    "description": native_schema.description,
                    "parameters": native_schema.input_schema,
                },
            }
            if self._include_examples() and native_schema.examples:
                schema_payload["examples"] = native_schema.examples
            schemas.append(schema_payload)
        return schemas

    def export_mcp_style_manifest(self) -> dict[str, object]:
        """Return a lightweight local MCP-style manifest structure."""
        if not self._compatibility_enabled("export_mcp_style_manifest", True):
            return {"service": {}, "tools": [], "generated_at": _utc_now()}
        manifest_config = self.config.get("manifest", {})
        tools: list[dict[str, object]] = []
        for native_schema in self.export_native_tool_schemas():
            tool_payload: dict[str, object] = {
                "name": native_schema.tool_name,
                "description": native_schema.description,
                "inputSchema": native_schema.input_schema,
                "annotations": {
                    "category": native_schema.category,
                    "outputSchema": native_schema.output_schema,
                },
            }
            if self._include_examples() and native_schema.examples:
                tool_payload["examples"] = native_schema.examples
            tools.append(tool_payload)

        return {
            "service": {
                "name": manifest_config.get("service_name", "data_governance_skills"),
                "version": manifest_config.get("version", "v1"),
                "description": manifest_config.get(
                    "description",
                    "Local governance tool platform",
                ),
            },
            "tools": tools,
            "generated_at": _utc_now(),
        }

    def build_capability_manifest(self) -> CapabilityManifest:
        """Build one summarized capability manifest for external adapter consumers."""
        manifest_config = self.config.get("manifest", {})
        tools = [
            {
                "name": schema.tool_name,
                "description": schema.description,
                "category": schema.category,
                "input_model": schema.input_model,
                "output_model": schema.output_model,
                "input_schema": schema.input_schema,
                "output_schema": schema.output_schema,
            }
            for schema in self.export_native_tool_schemas()
        ]
        return CapabilityManifest(
            service_name=str(manifest_config.get("service_name", "data_governance_skills")),
            version=str(manifest_config.get("version", "v1")),
            description=str(
                manifest_config.get("description", "Local governance tool platform")
            ),
            tools=tools,
            generated_at=_utc_now(),
        )


# TODO: extend schema export with richer model reflection once a real external protocol binding needs more complete JSON schema.
