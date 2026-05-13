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
