"""Static schema definitions and examples for adapter schema export."""

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
            "ai_ready_scores": {"type": "array", "items": {"type": "object"}},
            "ai_ready_summary": {"type": "object"},
            "rag_quality_issues": {"type": "array", "items": {"type": "object"}},
            "rag_quality_summary": {"type": "object"},
            "rag_quality_assessment": {"type": "object"},
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
    "RagQualityAssessmentArguments": {
        "type": "object",
        "properties": {
            "documents": {"type": "array", "items": {"type": "object"}},
            "chunks": {"type": "array", "items": {"type": "object"}},
            "retrieval_logs": {"type": "array", "items": {"type": "object"}},
            "answer_evaluations": {"type": "array", "items": {"type": "object"}},
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
    "assess_rag_quality": [
        {
            "documents": [
                {
                    "document_id": "std_v1",
                    "title": "Data Standard Policy",
                    "source": "governance_portal",
                    "version": "v1",
                    "permission_label": "internal",
                }
            ],
            "chunks": [
                {
                    "chunk_id": "chunk_1",
                    "document_id": "std_v1",
                    "content": "Customer ID is the unique identifier for customers.",
                    "permission_label": "internal",
                    "embedding_id": "emb_1",
                }
            ],
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
