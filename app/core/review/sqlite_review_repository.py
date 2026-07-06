"""SQLite-backed repository for machine-written review override state."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.core.utils.file_utils import ensure_directory
from app.core.utils.time_utils import utc_now_seconds


def connect_review_db(db_path: Path) -> sqlite3.Connection:
    ensure_directory(db_path.parent)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS review_records (
            record_type TEXT NOT NULL,
            record_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (record_type, record_key)
        )
        """
    )
    return connection


def save_review_payloads(
    db_path: Path,
    *,
    record_type: str,
    keyed_payloads: list[tuple[str, dict[str, object]]],
) -> None:
    timestamp = utc_now_seconds()
    with connect_review_db(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO review_records (
                record_type,
                record_key,
                payload_json,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(record_type, record_key) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            [
                (
                    record_type,
                    key,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    timestamp,
                )
                for key, payload in keyed_payloads
            ],
        )


def load_review_payloads(db_path: Path, *, record_type: str) -> list[dict[str, object]]:
    if not db_path.exists():
        return []
    with connect_review_db(db_path) as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM review_records
            WHERE record_type = ?
            ORDER BY record_key
            """,
            (record_type,),
        ).fetchall()
    return [json.loads(str(row[0])) for row in rows]
