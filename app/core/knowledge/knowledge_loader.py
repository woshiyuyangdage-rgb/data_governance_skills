"""Knowledge pack loaders for local governance dictionaries and standards."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.knowledge.knowledge_exceptions import (
    KnowledgePackColumnError,
    KnowledgePackError,
    KnowledgePackFileNotFoundError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ABBREVIATION_DICT_PATH = PROJECT_ROOT / "app" / "data" / "dictionaries" / "abbreviation_dict.csv"
ROOT_WORD_DICT_PATH = PROJECT_ROOT / "app" / "data" / "dictionaries" / "root_word_dict.csv"
STANDARD_FIELDS_PATH = PROJECT_ROOT / "app" / "data" / "standards" / "standard_fields.csv"

ABBREVIATION_REQUIRED_COLUMNS = [
    "abbreviation",
    "expanded_form",
    "category",
    "notes",
]
ROOT_WORD_REQUIRED_COLUMNS = [
    "token",
    "normalized_form",
    "category",
    "notes",
]
STANDARD_FIELDS_REQUIRED_COLUMNS = [
    "standard_code",
    "standard_name",
    "standard_name_cn",
    "description",
    "data_type",
    "business_domain",
    "aliases",
]


def _normalize_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized = dataframe.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]
    for column in normalized.columns:
        normalized[column] = normalized[column].apply(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    return normalized


def _load_csv_pack(file_path: Path, required_columns: list[str]) -> pd.DataFrame:
    if not file_path.exists():
        raise KnowledgePackFileNotFoundError(f"Knowledge pack file does not exist: {file_path}")

    try:
        dataframe = pd.read_csv(file_path)
    except Exception as exc:
        raise KnowledgePackError(f"Failed to load knowledge pack '{file_path}': {exc}") from exc

    dataframe = _normalize_dataframe(dataframe)
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise KnowledgePackColumnError(
            str(file_path),
            missing_columns,
            list(dataframe.columns),
        )

    ordered_columns = list(required_columns) + [
        column for column in dataframe.columns if column not in required_columns
    ]
    return dataframe[ordered_columns]


@lru_cache(maxsize=1)
def _load_abbreviation_dict_cached() -> pd.DataFrame:
    return _load_csv_pack(ABBREVIATION_DICT_PATH, ABBREVIATION_REQUIRED_COLUMNS)


@lru_cache(maxsize=1)
def _load_root_word_dict_cached() -> pd.DataFrame:
    return _load_csv_pack(ROOT_WORD_DICT_PATH, ROOT_WORD_REQUIRED_COLUMNS)


@lru_cache(maxsize=1)
def _load_standard_fields_cached() -> pd.DataFrame:
    return _load_csv_pack(STANDARD_FIELDS_PATH, STANDARD_FIELDS_REQUIRED_COLUMNS)


def load_abbreviation_dict() -> pd.DataFrame:
    """Load the abbreviation knowledge pack with light caching."""
    return _load_abbreviation_dict_cached().copy()


def load_root_word_dict() -> pd.DataFrame:
    """Load the root-word knowledge pack with light caching."""
    return _load_root_word_dict_cached().copy()


def load_standard_fields() -> pd.DataFrame:
    """Load the standard-fields knowledge pack with light caching."""
    return _load_standard_fields_cached().copy()
