"""Smoke tests for the governance task router."""

from pathlib import Path

import pandas as pd

from app.core.governance import batch_snapshot_store
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.stg_review_record import StgReviewRecord
from app.core.orchestrator.governance_router import GovernanceTaskRouter
from app.core.review import override_store, quality_override_store

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_governance_router_routes_major_profiles() -> None:
    router = GovernanceTaskRouter()

    profile_expectations = {
        "metadata_diagnosis_only": ["diagnosis"],
        "diagnosis_plus_mapping": ["diagnosis", "mapping"],
        "diagnosis_mapping_stg": ["diagnosis", "mapping", "stg"],
        "diagnosis_mapping_stg_quality": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
        ],
        "diagnosis_mapping_stg_quality_with_review": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "review_replay",
            "quality_review_replay",
        ],
        "diagnosis_mapping_stg_quality_package": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "execution_package_build",
        ],
        "diagnosis_mapping_stg_quality_package_with_review": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "review_replay",
            "quality_review_replay",
            "execution_package_build",
        ],
        "mapping_only": ["mapping"],
        "stg_only_from_mapping": ["mapping", "stg"],
        "quality_only_from_stg": ["mapping", "stg", "quality_rule_recommendation"],
        "quality_only_from_stg_with_review": [
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "quality_review_replay",
        ],
        "quality_package_only_from_confirmed": [
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "quality_review_replay",
            "execution_package_build",
        ],
        "governance_readiness_assessment": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "execution_package_build",
            "readiness_assessment",
            "gap_classification",
            "remediation_planning",
        ],
        "governance_readiness_assessment_with_review": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "review_replay",
            "quality_review_replay",
            "execution_package_build",
            "readiness_assessment",
            "gap_classification",
            "remediation_planning",
        ],
        "full_governance_work_package": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "review_replay",
            "quality_review_replay",
            "execution_package_build",
            "readiness_assessment",
            "gap_classification",
            "remediation_planning",
        ],
        "governance_delivery_package": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "execution_package_build",
            "readiness_assessment",
            "gap_classification",
            "remediation_planning",
            "backlog_build",
            "confirmation_workbook_export",
            "delivery_package_build",
        ],
        "confirmation_workbook_only": [
            "diagnosis",
            "mapping",
            "stg",
            "quality_rule_recommendation",
            "review_replay",
            "quality_review_replay",
            "execution_package_build",
            "readiness_assessment",
            "gap_classification",
            "remediation_planning",
            "backlog_build",
            "confirmation_workbook_export",
        ],
    }

    for profile_name, expected_stages in profile_expectations.items():
        response = router.run_task(
            GovernanceTaskRequest(
                file_path=str(SAMPLE_METADATA_PATH),
                profile_name=profile_name,
            )
        )

        assert response.profile_name == profile_name
        assert response.status == "success"
        assert response.stages_executed == expected_stages


def test_governance_router_routes_project_template() -> None:
    router = GovernanceTaskRouter()
    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="run_project_template",
            template_name="standard_mapping_confirmation_project",
            domain_pack_name="customer_domain_pack",
        )
    )

    assert response.status == "success"
    assert response.result.project_template_result is not None
    assert response.result.project_template_result.selected_domain_pack == "customer_domain_pack"


def test_governance_router_runs_with_intake_profile(tmp_path) -> None:
    file_path = tmp_path / "platform.csv"
    pd.DataFrame(
        [{"物理表名": "cust_table", "物理字段名": "cust_id", "字段类型": "varchar"}]
    ).to_csv(file_path, index=False)

    response = GovernanceTaskRouter().run_task(
        GovernanceTaskRequest(
            file_path=str(file_path),
            profile_name="metadata_diagnosis_only",
            intake_profile_name="governance_platform_export_template",
        )
    )

    assert response.status == "success"
    assert response.result.intake_normalization_result is not None
    assert response.result.intake_normalization_result.table_count == 1


def test_governance_router_can_apply_review_profile_and_export_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    router = GovernanceTaskRouter()
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "STG_OVERRIDES_PATH",
        tmp_path / "stg_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )

    override_store.save_mapping_review_records(
        [
            MappingReviewRecord(
                table_name="Sales Order Header",
                field_name="Order__ID",
                original_recommended_standard_code="transaction_id",
                final_standard_code="audit_log_id",
                review_action="edit",
                reviewer_note="router test mapping edit",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ]
    )
    override_store.save_stg_review_records(
        [
            StgReviewRecord(
                source_table_name="ods_customer_snapshot",
                source_field_name="snapshot_dt",
                original_recommended_stg_field_name="snapshot_date",
                final_stg_field_name="snapshot_business_date",
                original_recommended_data_type="date",
                final_data_type="timestamp",
                review_action="edit",
                reviewer_note="router test stg edit",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ]
    )

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="diagnosis_mapping_stg_with_review",
            apply_review_replay=True,
            export_reports=True,
            output_dir=str(tmp_path / "reports"),
        )
    )

    assert response.status == "success"
    assert response.stages_executed == ["diagnosis", "mapping", "stg", "review_replay"]
    assert response.exported_files is not None
    assert set(response.exported_files.keys()) == {"json", "markdown", "excel"}
    assert any(
        item.recommended_standard_code == "audit_log_id"
        for item in response.result.confirmed_mapping_results
    )
    assert any(
        item.recommended_stg_field_name == "snapshot_business_date"
        for item in response.result.confirmed_stg_suggestions
    )


def test_governance_router_routes_quality_profile() -> None:
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="diagnosis_mapping_stg_quality",
        )
    )

    assert response.status == "success"
    assert response.stages_executed == [
        "diagnosis",
        "mapping",
        "stg",
        "quality_rule_recommendation",
    ]
    assert response.result.quality_rule_suggestions
    assert isinstance(response.result.cross_field_quality_rules, list)
    assert response.result.quality_review_queue_summary["total_rule_count"] >= len(
        response.result.quality_rule_suggestions
    )


def test_governance_router_routes_quality_with_review_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    router = GovernanceTaskRouter()
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "STG_OVERRIDES_PATH",
        tmp_path / "stg_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_OVERRIDES_PATH",
        tmp_path / "quality_rule_overrides.csv",
    )
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_SESSIONS_DIR",
        tmp_path / "quality_rule_sessions",
    )
    quality_override_store.save_quality_rule_review_records(
        [
            QualityRuleReviewRecord(
                source_table_name="customer_master",
                source_field_name="customer_id",
                rule_type="not_null",
                original_rule_expression="not_null",
                final_rule_expression="not_null",
                original_severity="high",
                final_severity="high",
                review_action="accept",
                reviewer_note="router quality test",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ]
    )

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="diagnosis_mapping_stg_quality_with_review",
            apply_review_replay=True,
        )
    )

    assert response.status == "success"
    assert response.stages_executed == [
        "diagnosis",
        "mapping",
        "stg",
        "quality_rule_recommendation",
        "review_replay",
        "quality_review_replay",
    ]
    assert response.result.confirmed_quality_rules
    assert response.result.quality_rule_review_summary["confirmed_count"] == 1


def test_governance_router_routes_execution_package_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    router = GovernanceTaskRouter()
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_OVERRIDES_PATH",
        tmp_path / "quality_rule_overrides.csv",
    )
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_SESSIONS_DIR",
        tmp_path / "quality_rule_sessions",
    )
    quality_override_store.save_quality_rule_review_records(
        [
            QualityRuleReviewRecord(
                source_table_name="customer_master",
                source_field_name="customer_id",
                rule_type="not_null",
                original_rule_expression="not_null",
                final_rule_expression="not_null",
                original_severity="high",
                final_severity="high",
                review_action="accept",
                reviewer_note="router package test",
                reviewed_at="2026-05-01T10:00:00",
                source="test",
            )
        ]
    )

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="diagnosis_mapping_stg_quality_package_with_review",
            apply_review_replay=True,
        )
    )

    assert response.status == "success"
    assert response.stages_executed[-1] == "execution_package_build"
    assert response.result.execution_ready_package is not None
    assert response.result.execution_ready_package.rule_count == 1
    assert response.result.execution_package_summary["rule_count"] == 1


def test_governance_router_routes_readiness_work_package_profile() -> None:
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="full_governance_work_package",
        )
    )

    assert response.status == "success"
    assert response.stages_executed[-3:] == [
        "readiness_assessment",
        "gap_classification",
        "remediation_planning",
    ]
    assert response.result.readiness_scores
    assert response.result.ai_ready_scores
    assert response.result.governance_work_package is not None


def test_governance_router_routes_backlog_profile() -> None:
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="governance_backlog_build",
        )
    )

    assert response.status == "success"
    assert response.stages_executed[-1] == "backlog_build"
    assert response.result.remediation_actions
    assert response.result.governance_backlog_items
    assert response.result.backlog_summary is not None
    assert response.result.backlog_summary.total_items == len(
        response.result.governance_backlog_items
    )


def test_governance_router_routes_portfolio_profile() -> None:
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="governance_portfolio_assessment",
        )
    )

    assert response.status == "success"
    assert response.stages_executed[-3:] == [
        "backlog_sla",
        "portfolio_aggregation",
        "progress_snapshot",
    ]
    assert response.result.backlog_sla_statuses
    assert response.result.governance_portfolio_summary is not None
    assert response.result.progress_snapshot is not None


def test_governance_router_routes_delivery_package_profile() -> None:
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(SAMPLE_METADATA_PATH),
            profile_name="governance_delivery_package",
        )
    )

    assert response.status == "success"
    assert response.stages_executed[-2:] == [
        "confirmation_workbook_export",
        "delivery_package_build",
    ]
    assert response.result.confirmation_workbook_results
    assert response.result.governance_delivery_manifest is not None
    assert response.result.governance_delivery_package_result is not None


def test_governance_router_routes_batch_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(batch_snapshot_store, "SNAPSHOT_DIR", tmp_path)
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_paths=[str(SAMPLE_METADATA_PATH), str(SAMPLE_METADATA_PATH)],
            profile_name="batch_governance_run",
            base_filename="router_batch_test",
        )
    )

    assert response.status == "success"
    assert response.stages_executed[:5] == [
        "batch_load",
        "grouping",
        "fingerprint",
        "incremental_diff",
        "rerun_scope_selection",
    ]
    assert response.result.batch_group_results
    assert response.result.incremental_diff_summary is not None


def test_governance_router_routes_workbook_import_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )
    workbook_path = tmp_path / "mapping_import.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "source_table_name": "customer",
                    "source_field_name": "customer_id",
                    "recommended_standard_code": "customer_id",
                    "confirmation_status": "accepted",
                }
            ]
        ).to_excel(writer, sheet_name="mapping_confirmation", index=False)
    router = GovernanceTaskRouter()

    response = router.run_task(
        GovernanceTaskRequest(
            file_path=str(workbook_path),
            profile_name="import_confirmation_workbook",
            workbook_type="mapping_confirmation",
        )
    )

    assert response.status == "success"
    assert response.stages_executed == [
        "workbook_validate",
        "workbook_import",
        "roundtrip_merge",
    ]
    assert response.result.workbook_import_summaries[0].imported_count == 1


def test_governance_router_routes_template_aware_confirmation_import(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )
    workbook_path = tmp_path / "business_mapping_import.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "表名": "customer",
                    "字段名": "customer_id",
                    "标准编码": "customer_id",
                    "确认结果": "accepted",
                }
            ]
        ).to_excel(writer, sheet_name="mapping_review", index=False)

    response = GovernanceTaskRouter().run_task(
        GovernanceTaskRequest(
            file_path=str(workbook_path),
            profile_name="import_confirmation_with_template",
            workbook_type="mapping_confirmation",
        )
    )

    assert response.status == "success"
    assert response.stages_executed == [
        "confirmation_template_diagnosis",
        "workbook_import",
        "roundtrip_merge",
    ]
    assert response.result.confirmation_template_match_result is not None
    assert (
        response.result.confirmation_template_match_result.matched_template_name
        == "business_mapping_review_template"
    )
    assert response.result.workbook_import_summaries[0].imported_count == 1


def test_governance_router_routes_template_aware_import_and_rerun(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        override_store,
        "MAPPING_OVERRIDES_PATH",
        tmp_path / "mapping_overrides.csv",
    )
    monkeypatch.setattr(
        override_store,
        "REVIEW_SESSIONS_DIR",
        tmp_path / "review_sessions",
    )
    workbook_path = tmp_path / "business_mapping_rerun.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "表名": "customer",
                    "字段名": "customer_id",
                    "确认结果": "accepted",
                }
            ]
        ).to_excel(writer, sheet_name="mapping_review", index=False)

    response = GovernanceTaskRouter().run_task(
        GovernanceTaskRequest(
            file_path=str(workbook_path),
            profile_name="import_confirmation_template_and_rerun",
            workbook_type="mapping_confirmation",
        )
    )

    assert response.status == "success"
    assert response.stages_executed[-1] == "changed_object_rerun_scope"
    assert response.result.rerun_scope_summary["rerun_object_count"] == 1
