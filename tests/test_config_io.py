"""Tests for control-plane asset file I/O helpers."""

from pathlib import Path

from app.core.control_plane.config_io import (
    detect_asset_format,
    read_asset_file,
    write_asset_file,
)


def test_config_io_can_write_and_read_yaml(tmp_path: Path) -> None:
    file_path = tmp_path / "workflow_profiles.yaml"
    payload = {"profiles": [{"name": "demo", "enabled": True, "stages": ["diagnosis"]}]}

    write_asset_file(file_path, payload)
    loaded = read_asset_file(file_path)

    assert detect_asset_format(file_path) == "yaml"
    assert loaded["profiles"][0]["name"] == "demo"


def test_config_io_can_write_and_read_json(tmp_path: Path) -> None:
    file_path = tmp_path / "asset_registry.json"
    payload = {"assets": [{"asset_name": "workflow_profiles"}]}

    write_asset_file(file_path, payload)
    loaded = read_asset_file(file_path)

    assert detect_asset_format(file_path) == "json"
    assert loaded["assets"][0]["asset_name"] == "workflow_profiles"


def test_config_io_can_write_and_read_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "standard_fields.csv"
    payload = [
        {
            "standard_code": "customer_id",
            "standard_name": "customer_id",
            "standard_name_cn": "Customer ID",
        }
    ]

    write_asset_file(file_path, payload)
    loaded = read_asset_file(file_path)

    assert detect_asset_format(file_path) == "csv"
    assert loaded[0]["standard_code"] == "customer_id"
