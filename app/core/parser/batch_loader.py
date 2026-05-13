"""Batch metadata loading and grouping helpers."""

from collections import defaultdict

from app.core.models.table_meta import TableMeta
from app.core.parser.loader import load_metadata_file, load_metadata_with_intake_adapter
from app.core.rules.config_loader import get_batch_processing_policies_config


def load_metadata_files(file_paths: list[str]) -> list[TableMeta]:
    """Load multiple metadata files using the existing single-file parser."""
    tables: list[TableMeta] = []
    for file_path in file_paths:
        tables.extend(load_metadata_file(file_path))
    return tables


def load_metadata_files_with_intake_adapter(
    file_paths: list[str],
    profile_name: str | None = None,
) -> list[TableMeta]:
    """Load multiple metadata files through intake normalization."""
    tables: list[TableMeta] = []
    for file_path in file_paths:
        tables.extend(load_metadata_with_intake_adapter(file_path, profile_name=profile_name))
    return tables


def _normalize_group_value(value: object, fallback: str = "ungrouped") -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _infer_domain_hint(table: TableMeta) -> str:
    text_parts = [
        table.table_name,
        table.table_name_cn or "",
        table.table_description or "",
    ]
    text_parts.extend(field.field_name for field in table.fields)
    text = " ".join(text_parts).lower()
    domain_keywords = {
        "customer": ["customer", "cust", "客户"],
        "transaction": ["transaction", "order", "sales", "payment", "订单", "交易"],
        "product": ["product", "sku", "item", "商品", "产品"],
        "finance": ["amount", "currency", "invoice", "balance", "金额", "发票"],
        "audit": ["audit", "log", "created", "updated", "审计", "日志"],
    }
    for domain, keywords in domain_keywords.items():
        if any(keyword in text for keyword in keywords):
            return domain
    return "general"


def group_tables_by_field(
    tables: list[TableMeta],
    group_by: str = "system_name",
) -> dict[str, list[TableMeta]]:
    """Group tables by system, schema, or lightweight domain hint."""
    config = get_batch_processing_policies_config()
    supported_fields = set(config.get("supported_group_fields", []))
    if group_by not in supported_fields:
        raise ValueError(
            f"group_by must be one of: {', '.join(sorted(supported_fields))}"
        )

    grouped: dict[str, list[TableMeta]] = defaultdict(list)
    for table in tables:
        if group_by == "domain_hint":
            group_name = _infer_domain_hint(table)
        else:
            group_name = _normalize_group_value(getattr(table, group_by, None))
        grouped[group_name].append(table)
    return dict(grouped)

