"""Smoke tests for technical identification."""

from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta
from app.core.skills.metadata_diagnosis_skill import (
    TechnicalObjectIdentificationInput,
    TechnicalObjectIdentificationSkill,
)


def test_technical_identification_skill_smoke_run() -> None:
    skill = TechnicalObjectIdentificationSkill()
    table = TableMeta(
        table_name="tmp_order_log",
        table_name_cn="临时日志表",
        table_description="Temporary order log table.",
        fields=[
            FieldMeta(
                field_name="order_id",
                field_name_cn="order id",
                field_description="Order identifier.",
                data_type="string",
                nullable=False,
            )
        ],
    )

    result = skill.run(TechnicalObjectIdentificationInput(tables=[table]))

    assert result.identified_objects["tmp_order_log"] != "business_table"
    assert result.object_scores["tmp_order_log"]
    assert result.summary
