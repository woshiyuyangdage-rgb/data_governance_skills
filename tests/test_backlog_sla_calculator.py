"""Tests for backlog SLA calculation."""

from datetime import date

from app.core.governance.backlog_sla_calculator import BacklogSlaCalculator
from app.core.models.governance_backlog_item import GovernanceBacklogItem


def _policies() -> dict[str, object]:
    return {
        "default_due_days_by_priority": {
            "priority_governance": 7,
            "key_tracking": 14,
            "continuous_observation": 30,
        },
        "overdue_policy": {"warn_after_days": 3, "overdue_after_days": 0},
        "owner_role_due_day_adjustments": {
            "governance_lead": 0,
            "business_data_steward": 3,
        },
    }


def _item(
    backlog_id: str,
    priority: str = "key_tracking",
    owner_role: str = "business_data_steward",
    created_at: str = "2026-05-01T00:00:00",
    status: str = "proposed",
) -> GovernanceBacklogItem:
    return GovernanceBacklogItem(
        backlog_id=backlog_id,
        object_type="table",
        object_name="sales_order",
        gap_type="standard_mapping_gap",
        action="Review and confirm standard mappings",
        owner_role=owner_role,
        priority=priority,
        status=status,
        created_at=created_at,
    )


def test_sla_calculator_outputs_due_date_age_overdue_and_status() -> None:
    calculator = BacklogSlaCalculator(
        policies=_policies(),
        reference_date=date(2026, 5, 20),
    )

    statuses = calculator.calculate([_item("backlog_1")])

    assert len(statuses) == 1
    status = statuses[0]
    assert status.backlog_id == "backlog_1"
    assert status.due_date == "2026-05-18"
    assert status.age_days == 19
    assert status.overdue_days == 2
    assert status.is_overdue is True
    assert status.sla_status == "overdue"


def test_sla_calculator_marks_near_due_items_as_warning() -> None:
    calculator = BacklogSlaCalculator(
        policies=_policies(),
        reference_date=date(2026, 5, 7),
    )

    status = calculator.calculate(
        [
            _item(
                "backlog_warning",
                priority="priority_governance",
                owner_role="governance_lead",
            )
        ]
    )[0]

    assert status.due_date == "2026-05-08"
    assert status.is_overdue is False
    assert status.sla_status == "warning"


def test_sla_calculator_does_not_mark_completed_items_overdue() -> None:
    calculator = BacklogSlaCalculator(
        policies=_policies(),
        reference_date=date(2026, 6, 1),
    )

    status = calculator.calculate([_item("backlog_done", status="completed")])[0]

    assert status.overdue_days == 0
    assert status.is_overdue is False
    assert status.sla_status == "on_track"
