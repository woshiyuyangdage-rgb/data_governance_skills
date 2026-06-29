"""File-format-aware I/O helpers for control plane assets."""

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from app.core.utils.file_utils import ensure_directory


def detect_asset_format(file_path: str | Path) -> str:
    """Detect YAML, JSON, or CSV from a file extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return "csv"
    raise ValueError(f"Unsupported asset format: {file_path}")


def normalize_asset_content(file_path: str | Path, content: Any) -> Any:
    """Normalize editor or API input into the parsed asset representation."""
    asset_format = detect_asset_format(file_path)

    if asset_format == "yaml":
        if isinstance(content, str):
            return yaml.safe_load(content) or {}
        return content

    if asset_format == "json":
        if isinstance(content, str):
            if not content.strip():
                return {}
            return json.loads(content)
        return content

    if asset_format == "csv":
        if isinstance(content, pd.DataFrame):
            dataframe = content.copy()
        elif isinstance(content, str):
            if not content.strip():
                return []
            dataframe = pd.read_csv(StringIO(content))
        elif isinstance(content, list):
            dataframe = pd.DataFrame(content)
        elif isinstance(content, dict):
            if all(not isinstance(value, list) for value in content.values()):
                dataframe = pd.DataFrame([content])
            else:
                dataframe = pd.DataFrame(content)
        else:
            raise ValueError("CSV asset content must be text, list, dict, or dataframe.")
        dataframe = dataframe.where(pd.notna(dataframe), "")
        return dataframe.to_dict(orient="records")

    raise ValueError(f"Unsupported asset format: {file_path}")


def read_asset_file(file_path: str | Path) -> Any:
    """Read a managed asset file into a Python structure."""
    resolved_path = Path(file_path)
    asset_format = detect_asset_format(resolved_path)

    if asset_format == "yaml":
        return yaml.safe_load(resolved_path.read_text(encoding="utf-8")) or {}

    if asset_format == "json":
        return json.loads(resolved_path.read_text(encoding="utf-8"))

    if asset_format == "csv":
        dataframe = pd.read_csv(resolved_path)
        dataframe = dataframe.where(pd.notna(dataframe), "")
        return dataframe.to_dict(orient="records")

    raise ValueError(f"Unsupported asset format: {resolved_path}")


def write_asset_file(file_path: str | Path, content: Any) -> str:
    """Write one managed asset file from parsed or raw editor content."""
    resolved_path = Path(file_path)
    ensure_directory(resolved_path.parent)
    normalized_content = normalize_asset_content(resolved_path, content)
    asset_format = detect_asset_format(resolved_path)

    if asset_format == "yaml":
        resolved_path.write_text(
            yaml.safe_dump(
                normalized_content,
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return str(resolved_path)

    if asset_format == "json":
        resolved_path.write_text(
            json.dumps(normalized_content, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(resolved_path)

    if asset_format == "csv":
        dataframe = pd.DataFrame(normalized_content)
        dataframe = dataframe.where(pd.notna(dataframe), "")
        dataframe.to_csv(resolved_path, index=False)
        return str(resolved_path)

    raise ValueError(f"Unsupported asset format: {resolved_path}")
