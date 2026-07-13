"""Quality review, rule export, and execution-package route tests."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.routes_jobs import (
    ConfirmedQualityRuleExportRequest,
    ExecutionPackageBuildRequest,
    ExecutionPackageExportRequest,
    QualityRuleReviewRequest,
    build_execution_ready_package_route,
    execution_package_summary_route,
    export_confirmed_quality_rules_route,
    export_execution_ready_package_route,
    quality_rule_review_summary_route,
    review_quality_rules_route,
)
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.utils import file_utils


def test_quality_rule_review_and_summary_routes() -> None:
    confirmed_rule = ConfirmedQualityRule(
        source_table_name="sales_order",
        source_field_name="order_id",
        recommended_field_name="order_id",
        rule_type="not_null",
        rule_expression="not_null",
        severity="high",
        priority="P1",
        confirmation_source="override_accept",
    )
    response = review_quality_rules_route(
        QualityRuleReviewRequest(
            quality_rule_suggestions=[
                {
                    "source_table_name": "sales_order",
                    "source_field_name": "order_id",
                    "recommended_field_name": "order_id",
                    "rule_type": "not_null",
                    "rule_expression": "not_null",
                    "severity": "high",
                    "priority": "P1",
                    "recommendation_source": "test",
                }
            ],
            review_inputs={"sales_order.order_id.not_null": {"review_action": "accept"}},
            save_overrides=False,
        )
    )
    summary = quality_rule_review_summary_route()

    assert response["quality_rule_review_summary"]["confirmed_count"] == 1
    assert response["confirmed_quality_rules"][0]["rule_type"] == confirmed_rule.rule_type
    assert "accepted_count" in summary


def test_quality_rule_review_route_accepts_cross_field_rules() -> None:
    response = review_quality_rules_route(
        QualityRuleReviewRequest(
            cross_field_quality_rules=[
                CrossFieldQualityRule(
                    source_table_name="sales_order",
                    field_group=["start_date", "end_date"],
                    rule_type="temporal_order",
                    rule_expression="start_date <= end_date",
                    severity="medium",
                    confidence=1.0,
                    review_priority="medium_review_priority",
                    recommendation_source="cross_field_pattern",
                    match_basis="start_date/end_date",
                    reason="Start date should not be later than end date.",
                )
            ],
            review_inputs={},
            save_overrides=False,
        )
    )

    assert response["quality_rule_review_summary"]["confirmed_count"] == 1
    assert response["confirmed_quality_rules"][0]["rule_scope"] == "cross_field"
    assert response["confirmed_quality_rules"][0]["field_group"] == [
        "start_date",
        "end_date",
    ]


def test_export_confirmed_quality_rules_route(tmp_path: Path) -> None:
    response = export_confirmed_quality_rules_route(
        ConfirmedQualityRuleExportRequest(
            export_format="json",
            confirmed_quality_rules=[
                ConfirmedQualityRule(
                    source_table_name="sales_order",
                    source_field_name="order_id",
                    recommended_field_name="order_id",
                    rule_type="not_null",
                    rule_expression="not_null",
                    severity="high",
                    priority="P1",
                    confirmation_source="override_accept",
                )
            ],
            output_dir=str(tmp_path),
            base_filename="api_quality_rules",
        )
    )

    assert response["confirmed_rule_count"] == 1
    export_result = response["rule_export_results"][0]
    assert export_result["rule_count"] == 1
    assert Path(export_result["output_path"]).exists()


def test_export_confirmed_quality_rules_route_rejects_outside_output_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        export_confirmed_quality_rules_route(
            ConfirmedQualityRuleExportRequest(
                export_format="json",
                confirmed_quality_rules=[
                    ConfirmedQualityRule(
                        source_table_name="sales_order",
                        source_field_name="order_id",
                        recommended_field_name="order_id",
                        rule_type="not_null",
                        rule_expression="not_null",
                        severity="high",
                        priority="P1",
                        confirmation_source="override_accept",
                    )
                ],
                output_dir=str(outside_dir),
                base_filename="outside_quality_rules",
            )
        )

    assert exc_info.value.status_code == 400
    assert "outside allowed local roots" in str(exc_info.value.detail)
    assert not outside_dir.exists()


def test_execution_package_build_and_export_routes(tmp_path: Path) -> None:
    confirmed_rule = ConfirmedQualityRule(
        source_table_name="sales_order",
        source_field_name="order_id",
        recommended_field_name="order_id",
        rule_type="not_null",
        rule_expression="not_null",
        severity="high",
        priority="P1",
        confirmation_source="override_accept",
    )
    build_response = build_execution_ready_package_route(
        ExecutionPackageBuildRequest(
            confirmed_quality_rules=[confirmed_rule],
            profile_name="api_package_profile",
        )
    )
    package_payload = build_response["execution_ready_package"]
    export_response = export_execution_ready_package_route(
        ExecutionPackageExportRequest(
            export_format="manifest",
            execution_ready_package=package_payload,
            output_dir=str(tmp_path),
            base_filename="api_execution_package",
        )
    )
    summary_response = execution_package_summary_route()

    assert build_response["execution_package_summary"]["rule_count"] == 1
    assert package_payload["rules"][0]["rule_id"].startswith("rule_")
    export_result = export_response["execution_package_export_results"][0]
    assert export_result["rule_count"] == 1
    assert Path(export_result["output_path"]).exists()
    assert "supported_export_formats" in summary_response


def test_export_execution_ready_package_route_rejects_outside_output_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        export_execution_ready_package_route(
            ExecutionPackageExportRequest(
                export_format="manifest",
                confirmed_quality_rules=[
                    ConfirmedQualityRule(
                        source_table_name="sales_order",
                        source_field_name="order_id",
                        recommended_field_name="order_id",
                        rule_type="not_null",
                        rule_expression="not_null",
                        severity="high",
                        priority="P1",
                        confirmation_source="override_accept",
                    )
                ],
                output_dir=str(outside_dir),
                base_filename="outside_execution_package",
            )
        )

    assert exc_info.value.status_code == 400
    assert "outside allowed local roots" in str(exc_info.value.detail)
    assert not outside_dir.exists()
