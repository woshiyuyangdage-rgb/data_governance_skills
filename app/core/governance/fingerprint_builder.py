"""Object fingerprint builder for lightweight incremental rerun."""

import json
from hashlib import sha256
from typing import Any

from app.core.models.object_fingerprint import ObjectFingerprint
from app.core.models.table_meta import TableMeta
from app.core.rules.config_loader import get_incremental_rerun_policies_config


def normalize_for_fingerprint(value: Any) -> Any:
    """Normalize primitive values before stable hash generation."""
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.strip().lower().split())
    if isinstance(value, list):
        return [normalize_for_fingerprint(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): normalize_for_fingerprint(value[key])
            for key in sorted(value)
        }
    return value


class FingerprintBuilder:
    """Build table-level fingerprints from metadata and configured policy."""

    def __init__(self) -> None:
        self.config = get_incremental_rerun_policies_config()
        self.policy = dict(self.config.get("fingerprint_policy", {}))

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        normalized = normalize_for_fingerprint(payload)
        raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        return sha256(raw.encode("utf-8")).hexdigest()

    def build_table_fingerprint(
        self,
        table: TableMeta,
        group_name: str | None = None,
        source_file: str | None = None,
    ) -> ObjectFingerprint:
        """Build one table-level metadata fingerprint."""
        payload: dict[str, Any] = {
            "table_name": table.table_name,
            "table_name_cn": table.table_name_cn,
            "schema_name": table.schema_name,
            "system_name": table.system_name,
        }
        if bool(self.policy.get("include_table_description", True)):
            payload["table_description"] = table.table_description
        if bool(self.policy.get("include_table_fields", True)):
            fields = []
            for field in sorted(table.fields, key=lambda item: item.field_name):
                field_payload: dict[str, Any] = {}
                if bool(self.policy.get("include_field_names", True)):
                    field_payload["field_name"] = field.field_name
                    field_payload["field_name_cn"] = field.field_name_cn
                if bool(self.policy.get("include_field_descriptions", True)):
                    field_payload["field_description"] = field.field_description
                if bool(self.policy.get("include_data_types", True)):
                    field_payload["data_type"] = field.data_type
                    field_payload["nullable"] = field.nullable
                fields.append(field_payload)
            payload["fields"] = fields
        object_name = ".".join(
            part
            for part in [table.system_name, table.schema_name, table.table_name]
            if part
        )
        return ObjectFingerprint(
            object_type="table",
            object_name=object_name or table.table_name,
            group_name=group_name,
            fingerprint=self._hash_payload(payload),
            source_file=source_file,
        )

    def build_grouped_fingerprints(
        self,
        grouped_tables: dict[str, list[TableMeta]],
        source_file: str | None = None,
    ) -> list[ObjectFingerprint]:
        """Build fingerprints for all grouped tables."""
        fingerprints: list[ObjectFingerprint] = []
        for group_name, tables in grouped_tables.items():
            fingerprints.extend(
                self.build_table_fingerprint(
                    table,
                    group_name=group_name,
                    source_file=source_file,
                )
                for table in tables
            )
        return fingerprints

