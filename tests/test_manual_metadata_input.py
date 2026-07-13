"""Tests for hand-entered metadata input helpers."""

from pathlib import Path

import pytest

from app.core.parser.loader import load_metadata_file
from app.core.parser.manual_metadata_input import (
    manual_metadata_records_to_tables,
    save_manual_metadata_records,
)
from app.core.parser.parser_exceptions import ParserError
from app.core.utils import file_utils


def test_manual_metadata_records_convert_to_tables_with_carried_table_context() -> None:
    tables = manual_metadata_records_to_tables(
        [
            {
                "table_name": "contract_info",
                "table_name_cn": "合同信息",
                "table_description": "融资合同基础信息",
                "business_domain": "finance",
                "field_name": "contract_no",
                "field_name_cn": "合同编号",
                "field_description": "合同唯一编号",
                "data_type": "varchar",
                "nullable": "false",
                "is_primary_key": "true",
            },
            {
                "field_name": "contract_amt",
                "field_name_cn": "合同金额",
                "field_description": "合同约定金额",
                "data_type": "decimal",
                "nullable": "false",
            },
        ]
    )

    assert len(tables) == 1
    assert tables[0].table_name == "contract_info"
    assert tables[0].table_name_cn == "合同信息"
    assert tables[0].business_domain == "finance"
    assert [field.field_name for field in tables[0].fields] == [
        "contract_no",
        "contract_amt",
    ]
    assert tables[0].fields[0].nullable is False
    assert tables[0].fields[0].is_primary_key is True


def test_save_manual_metadata_records_creates_reusable_csv(tmp_path: Path) -> None:
    file_path = save_manual_metadata_records(
        [
            {
                "table_name": "customer_master",
                "table_name_cn": "客户主数据",
                "field_name": "customer_id",
                "field_description": "客户唯一编号",
                "data_type": "varchar",
            }
        ],
        output_dir=tmp_path,
        base_filename="manual_customer",
    )

    assert Path(file_path).exists()
    tables = load_metadata_file(file_path)
    assert len(tables) == 1
    assert tables[0].table_name == "customer_master"
    assert tables[0].fields[0].field_name == "customer_id"


def test_save_manual_metadata_records_rejects_output_dir_outside_allowed_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(ParserError) as exc_info:
        save_manual_metadata_records(
            [
                {
                    "table_name": "customer_master",
                    "field_name": "customer_id",
                }
            ],
            output_dir=outside_dir,
        )

    assert "outside allowed local roots" in str(exc_info.value)
