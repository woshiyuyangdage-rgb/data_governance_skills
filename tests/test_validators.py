"""Tests for control-plane asset validators."""

from app.core.control_plane.validators import validate_asset_content


def test_workflow_profiles_validator_accepts_valid_profiles() -> None:
    result = validate_asset_content(
        "workflow_profiles",
        {
            "profiles": [
                {
                    "name": "metadata_diagnosis_only",
                    "enabled": True,
                    "stages": ["diagnosis"],
                }
            ]
        },
    )

    assert result.is_valid is True
    assert result.messages == []


def test_intent_patterns_validator_rejects_missing_keywords() -> None:
    result = validate_asset_content(
        "intent_patterns",
        {
            "intents": {
                "quick_scan": {
                    "profile_name": "metadata_diagnosis_only",
                    "keywords": [],
                }
            },
            "parameters": {},
        },
    )

    assert result.is_valid is False
    assert any("at least one keyword" in message for message in result.messages)


def test_tool_registry_validator_accepts_valid_tools() -> None:
    result = validate_asset_content(
        "tool_registry",
        {
            "tools": [
                {
                    "name": "run_governance_profile",
                    "handler": "governance_tool_executor.run_governance_profile",
                    "enabled": True,
                }
            ]
        },
    )

    assert result.is_valid is True


def test_domain_governance_packs_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "domain_governance_packs",
        {
            "packs": [
                {
                    "pack_name": "customer_domain_pack",
                    "enabled": True,
                    "trigger_tokens": ["customer"],
                }
            ]
        },
    )

    assert result.is_valid is True


def test_project_template_profiles_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "project_template_profiles",
        {
            "templates": [
                {
                    "template_name": "metadata_inventory_project",
                    "enabled": True,
                    "base_workflow_profile": "metadata_diagnosis_only",
                }
            ]
        },
    )

    assert result.is_valid is True


def test_domain_delivery_templates_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "domain_delivery_templates",
        {
            "delivery_defaults": {
                "customer_domain_pack": {
                    "include_outputs": ["mapping_confirmation_workbook"]
                }
            }
        },
    )

    assert result.is_valid is True


def test_intake_template_profiles_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "intake_template_profiles",
        {
            "profiles": [
                {
                    "profile_name": "standard_metadata_template",
                    "enabled": True,
                    "required_target_fields": ["table_name", "field_name"],
                    "mapping_spec_name": "standard_metadata_spec",
                }
            ]
        },
    )

    assert result.is_valid is True


def test_intake_field_mapping_specs_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "intake_field_mapping_specs",
        {"mapping_specs": {"standard_metadata_spec": {"table_name": ["table_name"]}}},
    )

    assert result.is_valid is True


def test_intake_diagnosis_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "intake_diagnosis_policies",
        {
            "diagnosis_policy": {"trim_whitespace": True},
            "matching_policy": {"exact_header_score": 1.0},
            "validation_policy": {"allow_unknown_extra_columns": True},
        },
    )

    assert result.is_valid is True


def test_standard_fields_validator_rejects_duplicate_standard_codes() -> None:
    result = validate_asset_content(
        "standard_fields",
        [
            {
                "standard_code": "customer_id",
                "standard_name": "customer_id",
                "standard_name_cn": "Customer ID",
            },
            {
                "standard_code": "customer_id",
                "standard_name": "customer_identifier",
                "standard_name_cn": "Customer Identifier",
            },
        ],
    )

    assert result.is_valid is False
    assert any("must be unique" in message for message in result.messages)


def test_standard_mapping_semantic_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "standard_mapping_semantic",
        {
            "enabled": True,
            "model_name_or_path": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "local_files_only": True,
            "threshold": 0.85,
            "candidate_limit": 3,
            "standard_text_fields": [
                "standard_name",
                "standard_name_cn",
                "description",
            ],
            "source_text_fields": [
                "field_name",
                "field_name_cn",
                "field_description",
            ],
        },
    )

    assert result.is_valid is True


def test_standard_mapping_semantic_validator_rejects_invalid_threshold() -> None:
    result = validate_asset_content(
        "standard_mapping_semantic",
        {
            "enabled": True,
            "model_name_or_path": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "local_files_only": True,
            "threshold": 1.5,
            "candidate_limit": 3,
            "standard_text_fields": ["standard_name"],
            "source_text_fields": ["field_name"],
        },
    )

    assert result.is_valid is False
    assert any("threshold" in message for message in result.messages)


def test_quality_rule_templates_validator_accepts_valid_templates() -> None:
    result = validate_asset_content(
        "quality_rule_templates",
        {
            "templates": {
                "identifier": [
                    {"rule_type": "not_null", "severity": "high"},
                    {"rule_type": "uniqueness", "severity": "high"},
                ]
            }
        },
    )

    assert result.is_valid is True


def test_quality_rule_policies_validator_rejects_missing_mappings() -> None:
    result = validate_asset_content(
        "quality_rule_policies",
        {
            "token_to_template_map": {},
        },
    )

    assert result.is_valid is False
    assert any("standard_code_to_template_map" in message for message in result.messages)


def test_execution_package_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "execution_package_policies",
        {
            "package_policy": {"include_only_confirmed_rules": True},
            "execution_priority_map": {"high": "P1", "medium": "P2", "low": "P3"},
            "default_execution_mode": {"not_null": "batch_validation"},
            "engine_compatibility": {
                "custom_json": {"enabled": True},
                "dbt": {"enabled": True},
            },
        },
    )

    assert result.is_valid is True


def test_rule_execution_templates_validator_rejects_missing_semantics() -> None:
    result = validate_asset_content(
        "rule_execution_templates",
        {"templates": {"not_null": {"engine_hints": {"dbt": "not_null"}}}},
    )

    assert result.is_valid is False
    assert any("semantic_type" in message for message in result.messages)


def test_domain_rule_templates_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "domain_rule_templates",
        {
            "domains": {
                "customer": {
                    "trigger_tokens": ["customer"],
                    "rules": [
                        {
                            "rule_type": "identifier_presence_group",
                            "required_tokens": ["id", "name"],
                            "severity": "medium",
                        }
                    ],
                }
            }
        },
    )

    assert result.is_valid is True


def test_cross_field_rule_patterns_validator_rejects_missing_triggers() -> None:
    result = validate_asset_content(
        "cross_field_rule_patterns",
        {
            "patterns": [
                {
                    "pattern_name": "bad_pattern",
                    "rule_type": "temporal_order",
                    "expression_template": "start_date <= end_date",
                    "severity": "medium",
                }
            ]
        },
    )

    assert result.is_valid is False
    assert any("trigger_fields or trigger_tokens" in message for message in result.messages)


def test_quality_review_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "quality_review_policies",
        {
            "review_priority": {
                "low_confidence_threshold": 0.4,
                "medium_confidence_threshold": 0.7,
            },
            "confidence_policy": {
                "exact_template_match": 1.0,
                "domain_token_match": 0.8,
                "stg_name_match": 0.7,
                "source_token_match": 0.6,
                "weak_hint_match": 0.4,
            },
        },
    )

    assert result.is_valid is True


def test_readiness_scoring_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "readiness_scoring_policies",
        {
            "dimensions": {
                "metadata_readiness": {"weight": 0.25},
                "mapping_readiness": {"weight": 0.20},
            },
            "thresholds": {"ready": 0.8, "partially_ready": 0.5, "not_ready": 0.0},
            "scoring_rules": {"unmapped_field_penalty": 0.08},
        },
    )

    assert result.is_valid is True


def test_governance_gap_taxonomy_validator_rejects_empty_gaps() -> None:
    result = validate_asset_content("governance_gap_taxonomy", {"gaps": []})

    assert result.is_valid is False
    assert any("gaps list" in message for message in result.messages)


def test_remediation_templates_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "remediation_templates",
        {
            "templates": {
                "metadata_completion_gap": {
                    "action": "Complete metadata",
                    "owner_role": "metadata_manager",
                    "expected_output": "completed metadata records",
                }
            }
        },
    )

    assert result.is_valid is True


def test_governance_backlog_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "governance_backlog_policies",
        {
            "backlog_policy": {
                "generate_from_remediation_actions": True,
                "default_status": "proposed",
            },
            "status_transition_policy": {
                "allowed_transitions": {
                    "proposed": ["accepted", "dropped"],
                    "accepted": ["in_progress", "blocked", "dropped"],
                    "in_progress": ["blocked", "completed"],
                    "blocked": ["in_progress", "dropped"],
                    "completed": [],
                    "dropped": [],
                }
            },
            "priority_mapping": {
                "key_tracking": {"urgency_score": 2},
            },
        },
    )

    assert result.is_valid is True


def test_backlog_status_templates_validator_rejects_empty_statuses() -> None:
    result = validate_asset_content("backlog_status_templates", {"statuses": {}})

    assert result.is_valid is False
    assert any("statuses" in message for message in result.messages)


def test_governance_portfolio_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "governance_portfolio_policies",
        {
            "portfolio_dimensions": ["owner_role", "priority", "status"],
            "summary_policy": {"include_owner_workload": True},
        },
    )

    assert result.is_valid is True


def test_backlog_sla_policies_validator_rejects_missing_due_days() -> None:
    result = validate_asset_content(
        "backlog_sla_policies",
        {"overdue_policy": {"warn_after_days": 3}},
    )

    assert result.is_valid is False
    assert any("default_due_days_by_priority" in message for message in result.messages)


def test_progress_snapshot_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "progress_snapshot_policies",
        {
            "snapshot_policy": {"include_completed_items": True},
            "trend_fields": ["total_backlog_items", "overdue_count"],
        },
    )

    assert result.is_valid is True


def test_governance_delivery_templates_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "governance_delivery_templates",
        {
            "templates": {
                "mapping_confirmation": {
                    "include_columns": ["source_table_name", "confirmation_status"]
                }
            }
        },
    )

    assert result.is_valid is True


def test_confirmation_workbook_policies_validator_requires_policies() -> None:
    result = validate_asset_content(
        "confirmation_workbook_policies",
        {"workbook_policy": {"include_summary_sheet": True}},
    )

    assert result.is_valid is False
    assert any("delivery_package_policy" in message for message in result.messages)


def test_batch_processing_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "batch_processing_policies",
        {
            "batch_policy": {"default_group_by": "system_name"},
            "supported_group_fields": ["system_name", "schema_name"],
        },
    )

    assert result.is_valid is True


def test_incremental_rerun_policies_validator_rejects_empty_categories() -> None:
    result = validate_asset_content(
        "incremental_rerun_policies",
        {
            "fingerprint_policy": {"include_table_fields": True},
            "diff_categories": [],
        },
    )

    assert result.is_valid is False
    assert any("diff_categories" in message for message in result.messages)


def test_workbook_import_policies_validator_accepts_valid_config() -> None:
    result = validate_asset_content(
        "workbook_import_policies",
        {
            "workbook_types": {"mapping_confirmation": {"main_sheet_candidates": ["data"]}},
            "confirmation_status_mapping": {"accepted": "accept"},
        },
    )

    assert result.is_valid is True


def test_workbook_column_aliases_validator_rejects_empty_aliases() -> None:
    result = validate_asset_content("workbook_column_aliases", {"aliases": {}})

    assert result.is_valid is False
    assert any("aliases" in message for message in result.messages)
