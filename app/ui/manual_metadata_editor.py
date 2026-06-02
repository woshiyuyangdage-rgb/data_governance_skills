"""State helpers for the manual metadata editor."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import pandas as pd

from app.core.parser.manual_metadata_input import MANUAL_METADATA_COLUMNS

MANUAL_METADATA_ROWS_KEY = "manual_metadata_rows"
MANUAL_METADATA_EDITOR_VERSION_KEY = "manual_metadata_editor_version"
MANUAL_METADATA_DELETE_COLUMN = "_delete"


def default_manual_metadata_rows() -> list[dict[str, object]]:
    """Return starter rows for small hand-entered metadata examples."""
    return [
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
            "table_name": "contract_info",
            "field_name": "contract_amt",
            "field_name_cn": "合同金额",
            "field_description": "合同约定金额",
            "data_type": "decimal",
            "nullable": "false",
        },
    ]


def blank_manual_metadata_row() -> dict[str, object]:
    """Return one blank row with all supported manual metadata columns."""
    return {column: "" for column in MANUAL_METADATA_COLUMNS}


def ensure_manual_metadata_rows(
    session_state: MutableMapping[str, Any],
) -> list[dict[str, object]]:
    """Initialize and return editable manual metadata rows."""
    if MANUAL_METADATA_ROWS_KEY not in session_state:
        session_state[MANUAL_METADATA_ROWS_KEY] = default_manual_metadata_rows()
    if MANUAL_METADATA_EDITOR_VERSION_KEY not in session_state:
        session_state[MANUAL_METADATA_EDITOR_VERSION_KEY] = 0
    return session_state[MANUAL_METADATA_ROWS_KEY]


def manual_metadata_rows_to_editor_dataframe(
    rows: list[dict[str, object]],
) -> pd.DataFrame:
    """Return rows as an editor dataframe with a delete checkbox column."""
    dataframe = pd.DataFrame(rows, columns=MANUAL_METADATA_COLUMNS)
    dataframe.insert(0, MANUAL_METADATA_DELETE_COLUMN, False)
    return dataframe


def editor_dataframe_to_manual_records(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    """Convert an editor dataframe back to manual metadata records."""
    if MANUAL_METADATA_DELETE_COLUMN in dataframe.columns:
        dataframe = dataframe.drop(columns=[MANUAL_METADATA_DELETE_COLUMN])
    return dataframe.reindex(columns=MANUAL_METADATA_COLUMNS).fillna("").to_dict("records")


def apply_manual_metadata_editor_changes(
    session_state: MutableMapping[str, Any],
    dataframe: pd.DataFrame,
) -> None:
    """Persist table edits from the data editor into session state."""
    session_state[MANUAL_METADATA_ROWS_KEY] = editor_dataframe_to_manual_records(dataframe)


def append_manual_metadata_row(session_state: MutableMapping[str, Any]) -> None:
    """Append one blank row and bump the editor version."""
    rows = list(ensure_manual_metadata_rows(session_state))
    rows.append(blank_manual_metadata_row())
    session_state[MANUAL_METADATA_ROWS_KEY] = rows
    bump_manual_metadata_editor_version(session_state)


def delete_selected_manual_metadata_rows(
    session_state: MutableMapping[str, Any],
    dataframe: pd.DataFrame,
) -> int:
    """Delete rows marked by the editor checkbox and return the deleted count."""
    if MANUAL_METADATA_DELETE_COLUMN not in dataframe.columns:
        return 0

    selected_mask = dataframe[MANUAL_METADATA_DELETE_COLUMN].fillna(False).astype(bool)
    deleted_count = int(selected_mask.sum())
    remaining = dataframe.loc[~selected_mask].drop(columns=[MANUAL_METADATA_DELETE_COLUMN])
    session_state[MANUAL_METADATA_ROWS_KEY] = (
        remaining.reindex(columns=MANUAL_METADATA_COLUMNS).fillna("").to_dict("records")
    )
    if deleted_count:
        bump_manual_metadata_editor_version(session_state)
    return deleted_count


def reset_manual_metadata_rows(session_state: MutableMapping[str, Any]) -> None:
    """Reset the editor back to starter rows."""
    session_state[MANUAL_METADATA_ROWS_KEY] = default_manual_metadata_rows()
    bump_manual_metadata_editor_version(session_state)


def bump_manual_metadata_editor_version(session_state: MutableMapping[str, Any]) -> None:
    """Force Streamlit to rebuild the editor widget after row operations."""
    current_version = int(session_state.get(MANUAL_METADATA_EDITOR_VERSION_KEY, 0))
    session_state[MANUAL_METADATA_EDITOR_VERSION_KEY] = current_version + 1


def manual_metadata_editor_version(session_state: MutableMapping[str, Any]) -> int:
    """Return the current editor widget version."""
    return int(session_state.get(MANUAL_METADATA_EDITOR_VERSION_KEY, 0))
