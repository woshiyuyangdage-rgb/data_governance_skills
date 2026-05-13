"""Tests for rule-based intent interpretation."""

from app.core.intent.intent_interpreter import IntentInterpreter


def test_quick_scan_intent_maps_to_diagnosis_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Help me run a quick diagnosis")

    assert intent.matched_profile_name == "metadata_diagnosis_only"
    assert intent.fallback_used is False


def test_standard_mapping_intent_can_enable_export_reports() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Run standard mapping and export reports")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "diagnosis_plus_mapping"
    assert task_request.export_reports is True


def test_structure_suggestion_intent_maps_to_stg_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Generate STG structure suggestions")

    assert intent.matched_profile_name == "diagnosis_mapping_stg"


def test_replay_confirmed_intent_maps_to_review_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Rerun with confirmed overrides")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "diagnosis_mapping_stg_with_review"
    assert task_request.profile_name == "diagnosis_mapping_stg_with_review"
    assert task_request.apply_review_replay is True


def test_quality_rule_intent_maps_to_quality_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Recommend data quality rules")

    assert intent.matched_profile_name == "diagnosis_mapping_stg_quality"


def test_execution_package_intent_maps_to_package_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Build an execution package for confirmed rules")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "diagnosis_mapping_stg_quality_package_with_review"
    assert task_request.profile_name == "diagnosis_mapping_stg_quality_package_with_review"
    assert task_request.apply_review_replay is True
    assert task_request.preferred_result_mode == "package"


def test_quality_intelligence_intent_maps_to_quality_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Find temporal rules and amount currency rules")

    assert intent.matched_profile_name == "diagnosis_mapping_stg_quality"
    assert intent.matched_intent_name == "quality_rule_recommendation"


def test_readiness_intent_maps_to_readiness_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Run governance readiness assessment")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "governance_readiness_assessment"
    assert task_request.profile_name == "governance_readiness_assessment"
    assert task_request.preferred_result_mode == "readiness"


def test_remediation_intent_maps_to_work_package_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Generate a remediation plan and work package")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "full_governance_work_package"
    assert task_request.profile_name == "full_governance_work_package"
    assert task_request.apply_review_replay is True
    assert task_request.preferred_result_mode == "remediation"


def test_backlog_intent_maps_to_backlog_build_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Build governance backlog tracking")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "governance_backlog_build"
    assert task_request.profile_name == "governance_backlog_build"
    assert task_request.apply_review_replay is False
    assert task_request.preferred_result_mode == "backlog"


def test_full_backlog_package_intent_maps_to_full_backlog_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Build the full governance backlog package")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "full_governance_backlog_package"
    assert task_request.profile_name == "full_governance_backlog_package"
    assert task_request.apply_review_replay is True
    assert task_request.preferred_result_mode == "backlog"


def test_portfolio_intent_maps_to_portfolio_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Show governance portfolio SLA and owner workload")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "governance_portfolio_assessment"
    assert task_request.profile_name == "governance_portfolio_assessment"
    assert task_request.preferred_result_mode == "portfolio"


def test_full_portfolio_package_intent_maps_to_full_portfolio_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("Build full governance portfolio package")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "full_governance_portfolio_package"
    assert task_request.profile_name == "full_governance_portfolio_package"
    assert task_request.apply_review_replay is True
    assert task_request.preferred_result_mode == "portfolio"


def test_delivery_package_intent_maps_to_delivery_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("生成治理交付包")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "governance_delivery_package_with_review"
    assert task_request.profile_name == "governance_delivery_package_with_review"
    assert task_request.apply_review_replay is True
    assert task_request.preferred_result_mode == "package"


def test_confirmation_workbook_intent_maps_to_workbook_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("导出确认表")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "confirmation_workbook_only"
    assert task_request.profile_name == "confirmation_workbook_only"
    assert task_request.preferred_result_mode == "workbook"


def test_batch_intent_maps_to_batch_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("批量处理这些元数据文件")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "batch_governance_run"
    assert task_request.profile_name == "batch_governance_run"
    assert task_request.preferred_result_mode == "batch"


def test_incremental_intent_maps_to_incremental_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("只重跑变化对象")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert intent.matched_profile_name == "batch_incremental_rerun"
    assert task_request.profile_name == "batch_incremental_rerun"
    assert task_request.preferred_result_mode == "incremental"


def test_workbook_import_intent_maps_to_import_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("导入确认表")
    task_request = interpreter.build_task_request(intent, "sample.xlsx")

    assert intent.matched_profile_name == "import_confirmation_workbook"
    assert task_request.profile_name == "import_confirmation_workbook"
    assert task_request.preferred_result_mode == "import"


def test_workbook_import_rerun_intent_maps_to_rerun_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("导入并重跑变化对象")
    task_request = interpreter.build_task_request(intent, "sample.xlsx")

    assert intent.matched_profile_name == "import_and_rerun_changed_objects"
    assert task_request.profile_name == "import_and_rerun_changed_objects"
    assert task_request.preferred_result_mode == "rerun"


def test_project_template_intent_extracts_template_and_domain_pack() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("用供应链金融模板跑全流程")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert task_request.profile_name == "run_project_template"
    assert task_request.template_name == "full_governance_delivery_project"
    assert task_request.domain_pack_name == "supply_chain_finance_domain_pack"
    assert task_request.preferred_result_mode == "template"


def test_standard_mapping_project_intent_extracts_template() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("启动标准映射确认项目")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert task_request.profile_name == "run_project_template"
    assert task_request.template_name == "standard_mapping_confirmation_project"


def test_intake_intent_extracts_profile_and_auto_match() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("用治理平台导出模板跑并自动识别元数据模板")
    task_request = interpreter.build_task_request(intent, "sample.csv")

    assert task_request.intake_profile_name == "governance_platform_export_template"
    assert task_request.auto_match_template is True
    assert task_request.preferred_result_mode == "intake"


def test_unknown_text_falls_back_to_diagnosis_profile() -> None:
    interpreter = IntentInterpreter()

    intent = interpreter.interpret("totally unrelated request text")

    assert intent.matched_profile_name == "metadata_diagnosis_only"
    assert intent.fallback_used is True
