"""Tests for local metadata completion."""

from pathlib import Path

import pandas as pd
import pytest

from app.core.parser import metadata_completion as metadata_completion_module
from app.core.parser.loader import load_metadata_file
from app.core.parser.metadata_completion import (
    apply_reviewed_completion_changes,
    apply_reviewed_completion_values,
    complete_metadata_dataframe,
    completion_change_key,
    metadata_completion_changes_to_dataframe,
    save_completed_metadata,
)


@pytest.fixture(autouse=True)
def empty_completion_memory(monkeypatch) -> None:
    """Keep completion tests independent from local learned metadata files."""
    monkeypatch.setattr(
        metadata_completion_module,
        "load_field_completion_memory",
        lambda: pd.DataFrame(),
    )
    monkeypatch.setattr(
        metadata_completion_module,
        "load_table_completion_memory",
        lambda: pd.DataFrame(),
    )


def test_metadata_completion_generates_field_cn_suggestions() -> None:
    result = complete_metadata_dataframe(
        pd.DataFrame(
            [
                {
                    "table_name": "customer_master",
                    "field_name": "cust_id",
                    "data_type": "varchar",
                },
                {
                    "table_name": "contract_info",
                    "field_name": "contract_amt",
                    "data_type": "decimal",
                },
            ]
        )
    )

    customer_row = result.dataframe[result.dataframe["field_name"] == "cust_id"].iloc[0]
    contract_row = result.dataframe[
        result.dataframe["field_name"] == "contract_amt"
    ].iloc[0]

    assert customer_row["field_name_cn"]
    assert contract_row["field_name_cn"]
    assert customer_row["field_name_cn"] in customer_row["field_description"]
    assert result.completed_count >= 4

    changes = metadata_completion_changes_to_dataframe(result.changes)
    assert {"change_key", "candidate_1", "candidate_2", "candidate_3", "final_value"}.issubset(
        set(changes.columns)
    )
    assert {"field_name_cn", "field_description"}.issubset(set(changes["column_name"]))
    assert changes["candidate_1"].notna().all()


def test_completion_requires_reviewed_acceptance_before_applying() -> None:
    source_dataframe = pd.DataFrame(
        [
            {
                "table_name": "customer_master",
                "field_name": "cust_id",
                "data_type": "varchar",
            }
        ]
    )
    suggestions = complete_metadata_dataframe(source_dataframe)

    rejected = apply_reviewed_completion_changes(
        source_dataframe,
        suggestions.changes,
        accepted_change_keys=set(),
    )
    assert pd.isna(rejected.dataframe.iloc[0]["field_name_cn"])

    accepted_keys = {
        completion_change_key(change)
        for change in suggestions.changes
        if change.column_name == "field_name_cn"
    }
    accepted = apply_reviewed_completion_changes(
        source_dataframe,
        suggestions.changes,
        accepted_keys,
    )

    assert accepted.dataframe.iloc[0]["field_name_cn"]
    assert pd.isna(accepted.dataframe.iloc[0]["field_description"])
    assert all(
        completion_change_key(change) in accepted_keys
        for change in accepted.changes
    )


def test_save_completed_metadata_persists_only_reviewed_changes(tmp_path: Path) -> None:
    source_dataframe = pd.DataFrame(
        [
            {
                "table_name": "transaction_detail",
                "field_name": "txn_amt",
                "data_type": "decimal",
            }
        ]
    )
    suggestions = complete_metadata_dataframe(source_dataframe)
    accepted_keys = {
        completion_change_key(change)
        for change in suggestions.changes
        if change.column_name == "field_name_cn"
    }
    reviewed = apply_reviewed_completion_changes(
        source_dataframe,
        suggestions.changes,
        accepted_keys,
    )

    saved = save_completed_metadata(reviewed, output_dir=tmp_path, base_filename="completed")

    assert saved.output_path is not None
    assert Path(saved.output_path).exists()
    tables = load_metadata_file(saved.output_path)
    assert tables[0].table_name == "transaction_detail"
    assert tables[0].fields[0].field_name_cn
    assert tables[0].fields[0].field_description is None


def test_completion_accepts_human_edited_final_value() -> None:
    source_dataframe = pd.DataFrame(
        [
            {
                "table_name": "customer_master",
                "field_name": "cust_id",
            }
        ]
    )
    suggestions = complete_metadata_dataframe(source_dataframe)
    field_name_change = next(
        change for change in suggestions.changes if change.column_name == "field_name_cn"
    )

    reviewed = apply_reviewed_completion_values(
        source_dataframe,
        suggestions.changes,
        {completion_change_key(field_name_change): "客户唯一编号"},
    )

    assert reviewed.dataframe.iloc[0]["field_name_cn"] == "客户唯一编号"
    assert reviewed.changes[0].completed_value == "客户唯一编号"
    assert reviewed.changes[0].source == "human_review"
