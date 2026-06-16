"""Parser tests for local metadata file ingestion."""

from pathlib import Path

import pandas as pd
import pytest

from app.core.parser.csv_parser import parse_csv
from app.core.parser.excel_parser import parse_excel
from app.core.parser.loader import load_metadata_file
from app.core.parser.parser_exceptions import MissingRequiredColumnsError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_parse_csv_with_sample_metadata_returns_grouped_tables() -> None:
    tables = parse_csv(str(SAMPLE_METADATA_PATH))

    assert len(tables) == 4

    customer_master = next(table for table in tables if table.table_name == "customer_master")
    assert customer_master.table_name_cn
    assert len(customer_master.fields) == 3
    assert customer_master.fields[0].field_name == "customer_id"
    assert customer_master.fields[0].nullable is False

    user_audit_log = next(table for table in tables if table.table_name == "user_audit_log")
    assert user_audit_log.system_name == "security"
    assert len(user_audit_log.fields) == 2
    assert any(field.field_name == "log_id" for field in user_audit_log.fields)


def test_parse_csv_supports_extended_metadata_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "extended_metadata.csv"
    csv_path.write_text(
        (
            "table_name,table_description,system_name,business_domain,owner_role,"
            "lifecycle_status,data_layer,catalog_path,standard_code,standard_name,"
            "sensitivity_label,primary_key_fields,foreign_key_fields,field_name,"
            "field_name_cn,field_description,data_type,nullable,field_standard_code,"
            "field_business_domain,is_sensitive\n"
            "order_detail,Order details,erp,order,steward,active,dwd,/catalog/order,"
            "order_detail,order_detail,internal,order_id;line_id,order_id,order_id,"
            "订单ID,Order identifier,varchar,false,transaction_id,order,true\n"
        ),
        encoding="utf-8",
    )

    tables = parse_csv(str(csv_path))

    assert len(tables) == 1
    table = tables[0]
    assert table.business_domain == "order"
    assert table.owner_role == "steward"
    assert table.primary_key_fields == ["order_id", "line_id"]
    assert table.fields[0].standard_code == "transaction_id"
    assert table.fields[0].is_sensitive is True


def test_parse_csv_supports_bilingual_template_headers(tmp_path: Path) -> None:
    csv_path = tmp_path / "bilingual_template.csv"
    csv_path.write_text(
        (
            "表英文名 / table_name,表中文名 / table_name_cn,表描述 / table_description,"
            "所属schema / schema_name,来源系统 / system_name,字段英文名 / field_name,"
            "字段中文名 / field_name_cn,字段描述 / field_description,数据类型 / data_type,"
            "是否可空 / nullable\n"
            "customer_master,客户主数据,Active customer master data.,dim,crm,customer_id,"
            "客户ID,Unique customer identifier.,varchar,false\n"
            "customer_master,客户主数据,Active customer master data.,dim,crm,customer_name,"
            "客户名称,Official customer display name.,varchar,false\n"
            "customer_master,客户主数据,Active customer master data.,dim,crm,created_dt,"
            "创建日期,Creation date of the customer record.,datetime,true\n"
        ),
        encoding="utf-8",
    )

    tables = parse_csv(str(csv_path))

    assert len(tables) == 1
    table = tables[0]
    assert table.table_name == "customer_master"
    assert table.table_name_cn == "客户主数据"
    assert len(table.fields) == 3
    assert [field.field_name for field in table.fields] == [
        "customer_id",
        "customer_name",
        "created_dt",
    ]
    assert table.fields[2].nullable is True


def test_parse_excel_with_sample_metadata_rows_returns_tables(tmp_path: Path) -> None:
    sample_df = pd.read_csv(SAMPLE_METADATA_PATH)
    excel_path = tmp_path / "sample_metadata.xlsx"
    sample_df.to_excel(excel_path, index=False)

    tables = parse_excel(str(excel_path))

    assert len(tables) == 4
    assert any(table.table_name == "Sales Order Header" for table in tables)


def test_load_metadata_file_supports_sample_csv() -> None:
    tables = load_metadata_file(str(SAMPLE_METADATA_PATH))

    assert len(tables) == 4
    assert tables[0].table_name == "customer_master"


def test_parse_csv_missing_required_columns_raises_error(tmp_path: Path) -> None:
    invalid_csv_path = tmp_path / "missing_table_name.csv"
    invalid_csv_path.write_text(
        "schema_name,field_name\nods,customer_id\n",
        encoding="utf-8",
    )

    with pytest.raises(MissingRequiredColumnsError) as exc_info:
        parse_csv(str(invalid_csv_path))

    assert "table_name" in str(exc_info.value)
