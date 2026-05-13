"""Tests for multi-file batch loader and grouping."""

from pathlib import Path

from app.core.parser.batch_loader import group_tables_by_field, load_metadata_files

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_batch_loader_loads_multiple_files() -> None:
    tables = load_metadata_files([str(SAMPLE_METADATA_PATH), str(SAMPLE_METADATA_PATH)])

    assert tables
    assert len(tables) >= 2


def test_group_tables_by_supported_fields() -> None:
    tables = load_metadata_files([str(SAMPLE_METADATA_PATH)])

    by_system = group_tables_by_field(tables, group_by="system_name")
    by_schema = group_tables_by_field(tables, group_by="schema_name")
    by_domain = group_tables_by_field(tables, group_by="domain_hint")

    assert by_system
    assert by_schema
    assert by_domain

