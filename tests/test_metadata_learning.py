"""Tests for local metadata completion learning memory."""

from pathlib import Path

import pandas as pd
import pytest

from app.core.parser import metadata_completion, metadata_learning
from app.core.parser.metadata_learning import (
    clear_metadata_completion_memory_by_field_key,
    learn_metadata_memory_from_dataframe,
    load_field_completion_memory,
    load_table_completion_memory,
    metadata_completion_memory_details,
    prune_invalid_metadata_completion_memory,
    summarize_metadata_completion_memory,
)
from app.core.utils import file_utils
from app.core.utils.file_utils import LocalPathAccessError


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


def test_learning_memory_rejects_output_dir_outside_allowed_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(LocalPathAccessError):
        learn_metadata_memory_from_dataframe(
            pd.DataFrame(
                [
                    {
                        "table_name": "customer_master",
                        "field_name": "customer_level",
                    }
                ]
            ),
            source="quality_sample.csv",
            output_dir=outside_dir,
        )

    assert not outside_dir.exists()


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


def test_metadata_completion_memory_health_flags_conflicts_and_invalid_rows() -> None:
    field_memory = pd.DataFrame(
        [
            {
                "field_key": "customer_id",
                "field_name": "cust_id",
                "field_name_cn": "Customer ID",
                "field_description": "Customer identifier.",
                "table_name": "customer_master",
            },
            {
                "field_key": "customer_id",
                "field_name": "cust_id",
                "field_name_cn": "Client ID",
                "field_description": "Client identifier.",
                "table_name": "customer_profile",
            },
            {
                "field_key": "",
                "field_name": "broken_field",
                "field_name_cn": "",
                "field_description": "",
                "table_name": "broken_table",
            },
        ]
    )
    table_memory = pd.DataFrame(
        [
            {
                "table_key": "customer_master",
                "table_name": "customer_master",
                "table_name_cn": "Customer master",
                "table_description": "Customer base table.",
            },
            {
                "table_key": "customer_master",
                "table_name": "customer_master",
                "table_name_cn": "Client master",
                "table_description": "Client base table.",
            },
            {
                "table_key": "empty_table",
                "table_name": "empty_table",
                "table_name_cn": "",
                "table_description": "",
            },
        ]
    )

    health = summarize_metadata_completion_memory(field_memory, table_memory)
    details = metadata_completion_memory_details(field_memory, table_memory)

    assert health.field_memory_count == 3
    assert health.table_memory_count == 3
    assert health.conflict_field_key_count == 1
    assert health.conflict_table_key_count == 1
    assert health.invalid_field_record_count == 1
    assert health.invalid_table_record_count == 1
    assert health.conflict_field_keys == ("customer_id",)
    assert health.conflict_table_keys == ("customer_master",)
    assert details["field_conflict_records"][0]["field_key"] == "customer_id"
    assert details["invalid_table_records"][0]["table_key"] == "empty_table"


def test_metadata_completion_memory_prunes_invalid_rows(tmp_path: Path) -> None:
    pd.DataFrame(
        [
            {
                "field_key": "customer_id",
                "field_name": "cust_id",
                "field_name_cn": "Customer ID",
                "field_description": "Customer identifier.",
                "table_name": "customer_master",
            },
            {
                "field_key": "",
                "field_name": "broken_field",
                "field_name_cn": "",
                "field_description": "",
                "table_name": "broken_table",
            },
        ],
        columns=metadata_learning.FIELD_MEMORY_COLUMNS,
    ).to_csv(tmp_path / "field_completion_memory.csv", index=False, encoding="utf-8")
    pd.DataFrame(
        [
            {
                "table_key": "customer_master",
                "table_name": "customer_master",
                "table_name_cn": "Customer master",
                "table_description": "Customer base table.",
            },
            {
                "table_key": "broken_table",
                "table_name": "broken_table",
                "table_name_cn": "",
                "table_description": "",
            },
        ],
        columns=metadata_learning.TABLE_MEMORY_COLUMNS,
    ).to_csv(tmp_path / "table_completion_memory.csv", index=False, encoding="utf-8")

    result = prune_invalid_metadata_completion_memory(tmp_path)
    fields = pd.read_csv(tmp_path / "field_completion_memory.csv")
    tables = pd.read_csv(tmp_path / "table_completion_memory.csv")

    assert result["removed_count"] == 2
    assert result["field_memory"]["removed_count"] == 1
    assert result["table_memory"]["removed_count"] == 1
    assert fields["field_key"].tolist() == ["customer_id"]
    assert tables["table_key"].tolist() == ["customer_master"]


def test_metadata_completion_memory_clears_one_field_key(tmp_path: Path) -> None:
    memory_path = tmp_path / "field_completion_memory.csv"
    pd.DataFrame(
        [
            {
                "field_key": "customer_id",
                "field_name": "cust_id",
                "field_name_cn": "Customer ID",
                "field_description": "Customer identifier.",
                "table_name": "customer_master",
            },
            {
                "field_key": "contract_id",
                "field_name": "contract_id",
                "field_name_cn": "Contract ID",
                "field_description": "Contract identifier.",
                "table_name": "contract_master",
            },
        ],
        columns=metadata_learning.FIELD_MEMORY_COLUMNS,
    ).to_csv(memory_path, index=False, encoding="utf-8")

    result = clear_metadata_completion_memory_by_field_key("customer_id", memory_path)
    fields = pd.read_csv(memory_path)

    assert result["status"] == "cleared"
    assert result["removed_count"] == 1
    assert fields["field_key"].tolist() == ["contract_id"]
