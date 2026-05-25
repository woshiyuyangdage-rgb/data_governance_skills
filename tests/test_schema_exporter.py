"""Tests for adapter-layer schema export."""

from app.core.adapters.schema_exporter import SchemaExporter


def test_schema_exporter_can_export_native_schemas() -> None:
    exporter = SchemaExporter()

    schemas = exporter.export_native_tool_schemas()

    assert schemas
    assert any(
        schema.tool_name == "run_governance_profile"
        and schema.input_model == "GovernanceTaskRequest"
        for schema in schemas
    )
    assert any(schema.tool_name == "list_config_assets" for schema in schemas)
    assert any(
        schema.tool_name == "recommend_quality_rules"
        and schema.input_model == "QualityRuleToolRequest"
        for schema in schemas
    )
    assert any(schema.tool_name == "recommend_quality_intelligence" for schema in schemas)
    assert any(schema.tool_name == "review_quality_rules" for schema in schemas)
    assert any(schema.tool_name == "batch_review_quality_rules" for schema in schemas)
    assert any(schema.tool_name == "export_confirmed_quality_rules" for schema in schemas)
    assert any(schema.tool_name == "build_execution_ready_package" for schema in schemas)
    assert any(schema.tool_name == "export_execution_ready_package" for schema in schemas)
    assert any(schema.tool_name == "assess_text_to_sql_readiness" for schema in schemas)
    assert any(schema.tool_name == "assess_governance_readiness" for schema in schemas)
    assert any(schema.tool_name == "build_governance_work_package" for schema in schemas)
    assert any(schema.tool_name == "build_governance_backlog" for schema in schemas)
    assert any(
        schema.tool_name == "update_governance_backlog_status" for schema in schemas
    )
    assert any(schema.tool_name == "list_governance_backlog_items" for schema in schemas)
    assert any(schema.tool_name == "assess_governance_portfolio" for schema in schemas)
    assert any(schema.tool_name == "generate_progress_snapshot" for schema in schemas)
    assert any(
        schema.tool_name == "list_governance_progress_snapshots" for schema in schemas
    )
    assert any(schema.tool_name == "export_confirmation_workbooks" for schema in schemas)
    assert any(
        schema.tool_name == "build_governance_delivery_package"
        and schema.input_model == "DeliveryPackageArguments"
        for schema in schemas
    )
    assert any(
        schema.tool_name == "run_batch_governance"
        and schema.input_model == "BatchGovernanceArguments"
        for schema in schemas
    )
    assert any(schema.tool_name == "run_incremental_rerun" for schema in schemas)
    assert any(schema.tool_name == "compare_governance_snapshots" for schema in schemas)
    assert any(
        schema.tool_name == "import_confirmation_workbook"
        and schema.input_model == "WorkbookImportArguments"
        for schema in schemas
    )
    assert any(schema.tool_name == "import_confirmation_and_rerun" for schema in schemas)
    assert any(schema.tool_name == "list_domain_governance_packs" for schema in schemas)
    assert any(schema.tool_name == "list_project_templates" for schema in schemas)
    assert any(schema.tool_name == "match_domain_governance_pack" for schema in schemas)
    assert any(
        schema.tool_name == "run_project_template"
        and schema.input_model == "ProjectTemplateRunArguments"
        for schema in schemas
    )
    assert any(schema.tool_name == "diagnose_metadata_intake_template" for schema in schemas)
    assert any(schema.tool_name == "normalize_metadata_input" for schema in schemas)
    assert any(schema.tool_name == "run_governance_with_intake_profile" for schema in schemas)


def test_schema_exporter_can_export_openai_style_schemas() -> None:
    exporter = SchemaExporter()

    schemas = exporter.export_openai_style_schemas()

    assert schemas
    assert any(item["function"]["name"] == "run_governance_profile" for item in schemas)
    assert any(item["function"]["name"] == "recommend_quality_rules" for item in schemas)
    assert any(
        item["function"]["name"] == "recommend_quality_intelligence"
        for item in schemas
    )
    assert any(item["function"]["name"] == "review_quality_rules" for item in schemas)
    assert any(item["function"]["name"] == "batch_review_quality_rules" for item in schemas)
    assert any(
        item["function"]["name"] == "export_confirmed_quality_rules" for item in schemas
    )
    assert any(
        item["function"]["name"] == "build_execution_ready_package" for item in schemas
    )
    assert any(
        item["function"]["name"] == "export_execution_ready_package" for item in schemas
    )
    assert any(
        item["function"]["name"] == "assess_text_to_sql_readiness"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "assess_governance_readiness" for item in schemas
    )
    assert any(
        item["function"]["name"] == "build_governance_work_package" for item in schemas
    )
    assert any(
        item["function"]["name"] == "build_governance_backlog" for item in schemas
    )
    assert any(
        item["function"]["name"] == "update_governance_backlog_status"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "list_governance_backlog_items"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "assess_governance_portfolio"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "generate_progress_snapshot" for item in schemas
    )
    assert any(
        item["function"]["name"] == "list_governance_progress_snapshots"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "export_confirmation_workbooks"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "build_governance_delivery_package"
        for item in schemas
    )
    assert any(item["function"]["name"] == "run_batch_governance" for item in schemas)
    assert any(item["function"]["name"] == "run_incremental_rerun" for item in schemas)
    assert any(
        item["function"]["name"] == "compare_governance_snapshots"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "import_confirmation_workbook"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "import_confirmation_and_rerun"
        for item in schemas
    )
    assert any(item["function"]["name"] == "run_project_template" for item in schemas)
    assert any(
        item["function"]["name"] == "match_domain_governance_pack"
        for item in schemas
    )
    assert any(
        item["function"]["name"] == "diagnose_metadata_intake_template"
        for item in schemas
    )
    assert all(item["type"] == "function" for item in schemas)


def test_schema_exporter_can_export_mcp_style_manifest() -> None:
    exporter = SchemaExporter()

    manifest = exporter.export_mcp_style_manifest()

    assert "service" in manifest
    assert "tools" in manifest
    assert any(tool["name"] == "validate_config_asset" for tool in manifest["tools"])
    assert any(tool["name"] == "recommend_quality_rules" for tool in manifest["tools"])
    assert any(tool["name"] == "recommend_quality_intelligence" for tool in manifest["tools"])
    assert any(tool["name"] == "review_quality_rules" for tool in manifest["tools"])
    assert any(tool["name"] == "batch_review_quality_rules" for tool in manifest["tools"])
    assert any(
        tool["name"] == "export_confirmed_quality_rules" for tool in manifest["tools"]
    )
    assert any(tool["name"] == "build_execution_ready_package" for tool in manifest["tools"])
    assert any(tool["name"] == "export_execution_ready_package" for tool in manifest["tools"])
    assert any(tool["name"] == "assess_text_to_sql_readiness" for tool in manifest["tools"])
    assert any(tool["name"] == "assess_governance_readiness" for tool in manifest["tools"])
    assert any(tool["name"] == "build_governance_work_package" for tool in manifest["tools"])
    assert any(tool["name"] == "build_governance_backlog" for tool in manifest["tools"])
    assert any(
        tool["name"] == "update_governance_backlog_status"
        for tool in manifest["tools"]
    )
    assert any(
        tool["name"] == "list_governance_backlog_items"
        for tool in manifest["tools"]
    )
    assert any(tool["name"] == "assess_governance_portfolio" for tool in manifest["tools"])
    assert any(tool["name"] == "generate_progress_snapshot" for tool in manifest["tools"])
    assert any(
        tool["name"] == "list_governance_progress_snapshots"
        for tool in manifest["tools"]
    )
    assert any(tool["name"] == "export_confirmation_workbooks" for tool in manifest["tools"])
    assert any(
        tool["name"] == "build_governance_delivery_package"
        for tool in manifest["tools"]
    )
    assert any(tool["name"] == "run_batch_governance" for tool in manifest["tools"])
    assert any(tool["name"] == "run_incremental_rerun" for tool in manifest["tools"])
    assert any(tool["name"] == "compare_governance_snapshots" for tool in manifest["tools"])
    assert any(tool["name"] == "import_confirmation_workbook" for tool in manifest["tools"])
    assert any(tool["name"] == "import_confirmation_and_rerun" for tool in manifest["tools"])
    assert any(tool["name"] == "run_project_template" for tool in manifest["tools"])
    assert any(tool["name"] == "list_domain_governance_packs" for tool in manifest["tools"])
    assert any(tool["name"] == "normalize_metadata_input" for tool in manifest["tools"])


def test_schema_exporter_can_build_capability_manifest() -> None:
    exporter = SchemaExporter()

    manifest = exporter.build_capability_manifest()
    native_schemas = exporter.export_native_tool_schemas()

    assert manifest.service_name == "data_governance_skills"
    assert len(manifest.tools) == len(native_schemas)
