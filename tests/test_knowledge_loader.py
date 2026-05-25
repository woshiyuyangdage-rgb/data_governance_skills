"""Tests for governance knowledge pack loading."""

from pathlib import Path

import pytest

from app.core.knowledge.knowledge_exceptions import (
    KnowledgePackColumnError,
    KnowledgePackFileNotFoundError,
)
from app.core.knowledge.knowledge_loader import (
    ABBREVIATION_REQUIRED_COLUMNS,
    ROOT_WORD_REQUIRED_COLUMNS,
    STANDARD_FIELDS_REQUIRED_COLUMNS,
    _load_csv_pack,
    load_abbreviation_dict,
    load_root_word_dict,
    load_standard_fields,
)


def test_knowledge_pack_files_can_be_loaded() -> None:
    abbreviation_df = load_abbreviation_dict()
    root_word_df = load_root_word_dict()
    standard_fields_df = load_standard_fields()

    assert not abbreviation_df.empty
    assert not root_word_df.empty
    assert not standard_fields_df.empty
    assert set(ABBREVIATION_REQUIRED_COLUMNS).issubset(abbreviation_df.columns)
    assert set(ROOT_WORD_REQUIRED_COLUMNS).issubset(root_word_df.columns)
    assert set(STANDARD_FIELDS_REQUIRED_COLUMNS).issubset(standard_fields_df.columns)


def test_missing_knowledge_pack_file_raises_error(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing_pack.csv"

    with pytest.raises(KnowledgePackFileNotFoundError):
        _load_csv_pack(missing_file, ABBREVIATION_REQUIRED_COLUMNS)


def test_missing_knowledge_pack_columns_raise_error(tmp_path: Path) -> None:
    invalid_file = tmp_path / "invalid_pack.csv"
    invalid_file.write_text("abbreviation,notes\ncust,customer\n", encoding="utf-8")

    with pytest.raises(KnowledgePackColumnError) as exc_info:
        _load_csv_pack(invalid_file, ABBREVIATION_REQUIRED_COLUMNS)

    assert "expanded_form" in str(exc_info.value)


def test_load_csv_pack_preserves_optional_columns(tmp_path: Path) -> None:
    pack_file = tmp_path / "standard_fields.csv"
    pack_file.write_text(
        (
            "standard_code,standard_name,standard_name_cn,description,data_type,"
            "business_domain,aliases,data_length,value_domain\n"
            "customer_id,customer_id,Customer ID,Identifier,string,customer,"
            "cust_id,64,CUST001;CUST002\n"
        ),
        encoding="utf-8",
    )

    dataframe = _load_csv_pack(pack_file, STANDARD_FIELDS_REQUIRED_COLUMNS)

    assert "data_length" in dataframe.columns
    assert "value_domain" in dataframe.columns
