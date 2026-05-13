"""Tests for intake-aware metadata loader."""

import pandas as pd

from app.core.parser.loader import load_metadata_with_intake_adapter


def test_load_metadata_with_intake_adapter_normalizes_source_template(tmp_path) -> None:
    file_path = tmp_path / "inventory.csv"
    pd.DataFrame(
        [{"表名": "order_table", "字段名": "order_id", "类型": "varchar"}]
    ).to_csv(file_path, index=False)

    tables = load_metadata_with_intake_adapter(
        str(file_path),
        profile_name="manual_inventory_template",
    )

    assert len(tables) == 1
    assert tables[0].table_name == "order_table"
    assert tables[0].fields[0].field_name == "order_id"

