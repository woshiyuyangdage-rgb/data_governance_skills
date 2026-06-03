"""Tests for local metadata completion learning memory."""

from pathlib import Path

import pandas as pd

from app.core.parser import metadata_completion
from app.core.parser import metadata_learning
from app.core.parser.metadata_learning import (
    learn_metadata_memory_from_dataframe,
    load_field_completion_memory,
    load_table_completion_memory,
)


def test_learning_memory_extracts_quality_metadata(tmp_path: Path) -> None:
    summary = learn_metadata_memory_from_dataframe(
        pd.DataFrame(
            [
                {
                    "table_name": "customer_master",
                    "table_name_cn": "客户主数据",
                    "table_description": "记录客户基础信息。",
                    "field_name": "customer_level",
                    "field_name_cn": "客户等级",
                    "field_description": "客户分层等级。",
                }
            ]
        ),
        source="quality_sample.csv",
        output_dir=tmp_path,
    )

    field_memory = pd.read_csv(tmp_path / "field_completion_memory.csv")
    table_memory = pd.read_csv(tmp_path / "table_completion_memory.csv")

    assert summary.field_memory_count == 1
    assert summary.table_memory_count == 1
    assert field_memory.iloc[0]["field_name_cn"] == "客户等级"
    assert table_memory.iloc[0]["table_name_cn"] == "客户主数据"


def test_completion_prefers_learned_memory(monkeypatch, tmp_path: Path) -> None:
    learn_metadata_memory_from_dataframe(
        pd.DataFrame(
            [
                {
                    "table_name": "customer_master",
                    "table_name_cn": "客户主数据",
                    "table_description": "记录客户基础信息。",
                    "field_name": "customer_level",
                    "field_name_cn": "客户等级",
                    "field_description": "客户分层等级。",
                }
            ]
        ),
        source="quality_sample.csv",
        output_dir=tmp_path,
    )

    monkeypatch.setattr(
        metadata_completion,
        "load_field_completion_memory",
        lambda: metadata_learning._read_memory(
            tmp_path / "field_completion_memory.csv",
            metadata_learning.FIELD_MEMORY_COLUMNS,
        ),
    )
    monkeypatch.setattr(
        metadata_completion,
        "load_table_completion_memory",
        lambda: metadata_learning._read_memory(
            tmp_path / "table_completion_memory.csv",
            metadata_learning.TABLE_MEMORY_COLUMNS,
        ),
    )

    suggestions = metadata_completion.complete_metadata_dataframe(
        pd.DataFrame(
            [
                {
                    "table_name": "customer_master",
                    "field_name": "customer_level",
                }
            ]
        )
    )
    changes = {
        change.column_name: change
        for change in suggestions.changes
    }

    assert changes["table_name_cn"].candidate_values[0] == "客户主数据"
    assert changes["field_name_cn"].candidate_values[0] == "客户等级"
    assert changes["field_description"].candidate_values[0] == "客户分层等级。"
    assert changes["field_name_cn"].source == "learned_metadata_memory"


def test_learning_memory_loaders_return_empty_when_files_are_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(metadata_learning, "FIELD_MEMORY_PATH", tmp_path / "missing_fields.csv")
    monkeypatch.setattr(metadata_learning, "TABLE_MEMORY_PATH", tmp_path / "missing_tables.csv")

    assert load_field_completion_memory().empty
    assert load_table_completion_memory().empty
