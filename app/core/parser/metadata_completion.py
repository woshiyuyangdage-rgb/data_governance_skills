"""Local metadata completion helpers for uploaded or hand-entered metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pandas as pd

from app.core.knowledge.knowledge_loader import (
    load_abbreviation_dict,
    load_root_word_dict,
    load_standard_fields,
)
from app.core.models.table_meta import TableMeta
from app.core.normalize import expand_tokens, normalize_tokens, split_tokens
from app.core.parser._shared import STANDARD_COLUMNS
from app.core.parser.metadata_learning import (
    load_field_completion_memory,
    load_table_completion_memory,
    metadata_name_key,
)
from app.core.parser.loader import load_metadata_file
from app.core.utils.file_utils import ensure_directory, sanitize_filename

PROJECT_ROOT = Path(__file__).resolve().parents[3]
METADATA_COMPLETION_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "metadata_completion"

TOKEN_CN_MAP = {
    "account": "账户",
    "amount": "金额",
    "application": "申请",
    "audit": "审计",
    "balance": "余额",
    "category": "类别",
    "code": "编码",
    "configuration": "配置",
    "contract": "合同",
    "count": "数量",
    "created": "创建",
    "customer": "客户",
    "date": "日期",
    "detail": "明细",
    "event": "事件",
    "flag": "标识",
    "history": "历史",
    "identifier": "标识",
    "information": "信息",
    "invoice": "发票",
    "loan": "贷款",
    "log": "日志",
    "merchant": "商户",
    "message": "消息",
    "name": "名称",
    "number": "编号",
    "order": "订单",
    "payment": "支付",
    "price": "价格",
    "product": "产品",
    "quantity": "数量",
    "rate": "比率",
    "record": "记录",
    "repayment": "还款",
    "sales": "销售",
    "snapshot": "快照",
    "state": "状态",
    "status": "状态",
    "summary": "汇总",
    "temporary": "临时",
    "time": "时间",
    "trace": "跟踪",
    "transaction": "交易",
    "type": "类型",
    "updated": "更新",
    "user": "用户",
    "value": "值",
}


@dataclass(frozen=True)
class MetadataCompletionChange:
    """One human-reviewable metadata completion suggestion."""

    object_type: str
    table_name: str
    field_name: str | None
    column_name: str
    original_value: str | None
    completed_value: str
    confidence: float
    source: str
    evidence: list[str] = field(default_factory=list)
    candidate_values: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetadataCompletionResult:
    """Completed metadata preview, source rows, and change audit."""

    dataframe: pd.DataFrame
    changes: list[MetadataCompletionChange]
    output_path: str | None = None
    source_dataframe: pd.DataFrame | None = None

    @property
    def completed_count(self) -> int:
        return len(self.changes)


def completion_change_key(change: MetadataCompletionChange) -> str:
    """Return a stable key for one missing metadata cell."""
    return "::".join(
        [
            change.object_type,
            change.table_name,
            change.field_name or "",
            change.column_name,
        ]
    )


def _optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _prepare_metadata_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    prepared = dataframe.copy()
    for column in STANDARD_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = None
    return prepared[STANDARD_COLUMNS]


def _index_standard_rows() -> dict[str, dict[str, str]]:
    dataframe = load_standard_fields()
    lookup: dict[str, dict[str, str]] = {}
    for _, row in dataframe.iterrows():
        row_data = {
            column: _optional_text(row.get(column)) or ""
            for column in dataframe.columns
        }
        keys = [row_data.get("standard_code"), row_data.get("standard_name")]
        aliases = row_data.get("aliases") or ""
        keys.extend(alias.strip() for alias in aliases.split(";") if alias.strip())
        for key in keys:
            if key:
                lookup[key.lower()] = row_data
    return lookup


def _index_memory_rows(dataframe: pd.DataFrame, key_column: str) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    if dataframe.empty or key_column not in dataframe.columns:
        return lookup
    for _, row in dataframe.iterrows():
        key = _optional_text(row.get(key_column))
        if key:
            lookup[key] = {
                column: _optional_text(row.get(column)) or ""
                for column in dataframe.columns
            }
    return lookup


def _build_token_cn_map() -> dict[str, str]:
    mapping = dict(TOKEN_CN_MAP)
    for loader, source_column in [
        (load_abbreviation_dict, "expanded_form"),
        (load_root_word_dict, "normalized_form"),
    ]:
        try:
            dataframe = loader()
        except Exception:
            continue
        for _, row in dataframe.iterrows():
            token = _optional_text(row.get(source_column))
            if token and token.lower() in TOKEN_CN_MAP:
                mapping[token.lower()] = TOKEN_CN_MAP[token.lower()]
    return mapping


def _normalized_tokens(value: str | None) -> list[str]:
    return normalize_tokens(expand_tokens(split_tokens(value)))


def _candidate_keys(*values: object) -> list[str]:
    keys: list[str] = []
    for value in values:
        text = _optional_text(value)
        if not text:
            continue
        keys.append(text.lower())
        normalized = "_".join(_normalized_tokens(text))
        if normalized:
            keys.append(normalized)
    return list(dict.fromkeys(keys))


def _cn_from_tokens(name: str, token_cn_map: dict[str, str]) -> tuple[str | None, list[str]]:
    tokens = _normalized_tokens(name)
    cn_parts = [token_cn_map[token] for token in tokens if token in token_cn_map]
    if not cn_parts:
        return None, []
    return "".join(dict.fromkeys(cn_parts)), [f"tokens={','.join(tokens)}"]


def _field_cn_from_standard(
    field_name: str,
    standard_code: str | None,
    standard_name: str | None,
    standard_lookup: dict[str, dict[str, str]],
) -> tuple[str | None, list[str]]:
    for key in _candidate_keys(standard_code, standard_name, field_name):
        standard = standard_lookup.get(key)
        if standard and standard.get("standard_name_cn"):
            return standard["standard_name_cn"], [
                f"matched_standard={standard.get('standard_code') or key}"
            ]
    return None, []


def _unique_candidates(*values: str | None) -> list[str]:
    candidates: list[str] = []
    for value in values:
        text = _optional_text(value)
        if text and text not in candidates:
            candidates.append(text)
    while candidates and len(candidates) < 3:
        candidates.append(candidates[0])
    return candidates[:3]


def _cn_candidates(
    name: str,
    *,
    standard_cn: str | None,
    token_cn: str | None,
    object_suffix: str = "",
) -> list[str]:
    base = standard_cn or token_cn
    suffix_candidate = None
    if base and object_suffix and not base.endswith(object_suffix):
        suffix_candidate = f"{base}{object_suffix}"
    return _unique_candidates(
        standard_cn,
        token_cn,
        suffix_candidate,
        name.replace("_", " "),
    )


def _field_description_candidate(field_cn: str | None, field_name: str, table_name: str) -> str:
    label = field_cn or field_name.replace("_", " ")
    return f"表示{table_name}中的{label}，具体业务口径建议结合数据标准或业务规则确认。"


def _description_candidates(
    field_cn: str | None,
    field_name: str,
    table_name: str,
) -> list[str]:
    label = field_cn or field_name.replace("_", " ")
    return _unique_candidates(
        _field_description_candidate(field_cn, field_name, table_name),
        f"用于记录{table_name}中的{label}。",
        f"{label}字段，具体含义和统计口径需经业务确认。",
    )


def tables_to_metadata_dataframe(tables: Iterable[TableMeta]) -> pd.DataFrame:
    """Flatten table metadata objects into the standard row-based CSV shape."""
    rows: list[dict[str, object]] = []
    for table in tables:
        table_values = {
            "table_name": table.table_name,
            "table_name_cn": table.table_name_cn,
            "table_description": table.table_description,
            "schema_name": table.schema_name,
            "system_name": table.system_name,
            "business_domain": table.business_domain,
            "owner_role": table.owner_role,
            "lifecycle_status": table.lifecycle_status,
            "data_layer": table.data_layer,
            "catalog_path": table.catalog_path,
            "upstream_systems": ";".join(table.upstream_systems),
            "downstream_applications": ";".join(table.downstream_applications),
            "frequent_query_sql": table.frequent_query_sql,
            "usage_scenarios": table.usage_scenarios,
            "standard_code": table.standard_code,
            "standard_name": table.standard_name,
            "sensitivity_label": table.sensitivity_label,
            "primary_key_fields": ";".join(table.primary_key_fields),
            "foreign_key_fields": ";".join(table.foreign_key_fields),
        }
        if not table.fields:
            rows.append({**table_values, "field_name": None})
            continue
        for field_meta in table.fields:
            rows.append(
                {
                    **table_values,
                    "field_name": field_meta.field_name,
                    "field_name_cn": field_meta.field_name_cn,
                    "field_description": field_meta.field_description,
                    "data_type": field_meta.data_type,
                    "data_length": field_meta.data_length,
                    "sample_values": field_meta.sample_values,
                    "nullable": field_meta.nullable,
                    "field_standard_code": field_meta.standard_code,
                    "field_standard_name": field_meta.standard_name,
                    "field_business_domain": field_meta.business_domain,
                    "field_owner_role": field_meta.owner_role,
                    "field_lifecycle_status": field_meta.lifecycle_status,
                    "field_catalog_path": field_meta.catalog_path,
                    "is_primary_key": field_meta.is_primary_key,
                    "is_foreign_key": field_meta.is_foreign_key,
                    "is_sensitive": field_meta.is_sensitive,
                }
            )
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def complete_metadata_dataframe(dataframe: pd.DataFrame) -> MetadataCompletionResult:
    """Generate 3-option completion suggestions and a preview dataframe."""
    source_dataframe = _prepare_metadata_dataframe(dataframe)
    preview = source_dataframe.copy()
    standard_lookup = _index_standard_rows()
    field_memory_lookup = _index_memory_rows(load_field_completion_memory(), "field_key")
    table_memory_lookup = _index_memory_rows(load_table_completion_memory(), "table_key")
    token_cn_map = _build_token_cn_map()
    changes: list[MetadataCompletionChange] = []

    for index, row in preview.iterrows():
        table_name = _optional_text(row.get("table_name"))
        field_name = _optional_text(row.get("field_name"))
        if not table_name:
            continue

        if _optional_text(row.get("table_name_cn")) is None:
            learned_table = table_memory_lookup.get(metadata_name_key(table_name), {})
            learned_table_cn = _optional_text(learned_table.get("table_name_cn"))
            table_cn, evidence = _cn_from_tokens(table_name, token_cn_map)
            if learned_table_cn or table_cn:
                candidates = _cn_candidates(
                    table_name,
                    standard_cn=learned_table_cn,
                    token_cn=table_cn,
                    object_suffix="表",
                )
                preview.at[index, "table_name_cn"] = candidates[0]
                changes.append(
                    MetadataCompletionChange(
                        object_type="table",
                        table_name=table_name,
                        field_name=None,
                        column_name="table_name_cn",
                        original_value=None,
                        completed_value=candidates[0],
                        confidence=0.92 if learned_table_cn else 0.72,
                        source="learned_metadata_memory"
                        if learned_table_cn
                        else "root_word_dictionary",
                        evidence=(
                            [f"learned_table={learned_table.get('source')}"]
                            if learned_table_cn
                            else evidence
                        ),
                        candidate_values=candidates,
                    )
                )

        if not field_name:
            continue

        field_cn = _optional_text(row.get("field_name_cn"))
        learned_field = field_memory_lookup.get(metadata_name_key(field_name), {})
        if field_cn is None:
            learned_field_cn = _optional_text(learned_field.get("field_name_cn"))
            standard_cn, evidence = _field_cn_from_standard(
                field_name,
                _optional_text(row.get("field_standard_code"))
                or _optional_text(row.get("standard_code")),
                _optional_text(row.get("field_standard_name"))
                or _optional_text(row.get("standard_name")),
                standard_lookup,
            )
            token_cn, token_evidence = _cn_from_tokens(field_name, token_cn_map)
            source = (
                "learned_metadata_memory"
                if learned_field_cn
                else "standard_fields"
                if standard_cn
                else "root_word_dictionary"
            )
            confidence = 0.95 if learned_field_cn else 0.9 if standard_cn else 0.72
            candidates = _cn_candidates(
                field_name,
                standard_cn=learned_field_cn or standard_cn,
                token_cn=token_cn,
            )
            if candidates:
                field_cn = candidates[0]
                preview.at[index, "field_name_cn"] = field_cn
                changes.append(
                    MetadataCompletionChange(
                        object_type="field",
                        table_name=table_name,
                        field_name=field_name,
                        column_name="field_name_cn",
                        original_value=None,
                        completed_value=field_cn,
                        confidence=confidence,
                        source=source,
                        evidence=(
                            [f"learned_field={learned_field.get('source')}"]
                            if learned_field_cn
                            else evidence + token_evidence
                        ),
                        candidate_values=candidates,
                    )
                )

        if _optional_text(row.get("field_description")) is None and field_cn:
            learned_description = _optional_text(learned_field.get("field_description"))
            candidates = _unique_candidates(
                learned_description,
                *_description_candidates(field_cn, field_name, table_name),
            )
            preview.at[index, "field_description"] = candidates[0]
            changes.append(
                MetadataCompletionChange(
                    object_type="field",
                    table_name=table_name,
                    field_name=field_name,
                    column_name="field_description",
                    original_value=None,
                    completed_value=candidates[0],
                    confidence=0.9 if learned_description else 0.58,
                    source="learned_metadata_memory"
                    if learned_description
                    else "description_template",
                    evidence=(
                        [f"learned_field={learned_field.get('source')}"]
                        if learned_description
                        else [f"field_name_cn={field_cn}", f"table_name={table_name}"]
                    ),
                    candidate_values=candidates,
                )
            )

    return MetadataCompletionResult(
        dataframe=preview,
        changes=changes,
        source_dataframe=source_dataframe,
    )


def apply_reviewed_completion_changes(
    dataframe: pd.DataFrame,
    changes: Iterable[MetadataCompletionChange],
    accepted_change_keys: set[str],
) -> MetadataCompletionResult:
    """Apply accepted completion suggestions using their first candidate value."""
    accepted_values = {
        completion_change_key(change): change.completed_value
        for change in changes
        if completion_change_key(change) in accepted_change_keys
    }
    return apply_reviewed_completion_values(dataframe, changes, accepted_values)


def apply_reviewed_completion_values(
    dataframe: pd.DataFrame,
    changes: Iterable[MetadataCompletionChange],
    accepted_values: dict[str, str],
) -> MetadataCompletionResult:
    """Apply human-reviewed final values keyed by completion change key."""
    source_dataframe = _prepare_metadata_dataframe(dataframe)
    reviewed = source_dataframe.copy()
    accepted_changes: list[MetadataCompletionChange] = []

    for change in changes:
        final_value = _optional_text(accepted_values.get(completion_change_key(change)))
        if not final_value:
            continue
        row_mask = (
            reviewed["table_name"].map(_optional_text).eq(change.table_name)
            & reviewed["field_name"].map(_optional_text).fillna("").eq(change.field_name or "")
        )
        if change.field_name is None:
            row_mask = reviewed["table_name"].map(_optional_text).eq(change.table_name)
        matching_indexes = list(reviewed.index[row_mask])
        if not matching_indexes:
            continue
        for index in matching_indexes:
            if _optional_text(reviewed.at[index, change.column_name]) is None:
                reviewed.at[index, change.column_name] = final_value
        accepted_changes.append(
            MetadataCompletionChange(
                object_type=change.object_type,
                table_name=change.table_name,
                field_name=change.field_name,
                column_name=change.column_name,
                original_value=change.original_value,
                completed_value=final_value,
                confidence=change.confidence,
                source="human_review",
                evidence=change.evidence + ["human_reviewed_final_value"],
                candidate_values=change.candidate_values,
            )
        )

    return MetadataCompletionResult(
        dataframe=reviewed,
        changes=accepted_changes,
        source_dataframe=source_dataframe,
    )


def complete_metadata_tables(tables: Iterable[TableMeta]) -> MetadataCompletionResult:
    """Generate metadata completion suggestions for loaded table metadata."""
    return complete_metadata_dataframe(tables_to_metadata_dataframe(tables))


def complete_metadata_file(file_path: str | Path) -> MetadataCompletionResult:
    """Load a metadata file and return completion suggestions."""
    return complete_metadata_tables(load_metadata_file(str(file_path)))


def save_completed_metadata(
    result: MetadataCompletionResult,
    output_dir: str | Path | None = None,
    *,
    base_filename: str | None = None,
) -> MetadataCompletionResult:
    """Persist a reviewed metadata dataframe and return an updated result."""
    target_dir = Path(output_dir or METADATA_COMPLETION_OUTPUT_DIR)
    ensure_directory(target_dir)
    base_name = sanitize_filename(base_filename or "completed_metadata")
    destination = target_dir / f"{Path(base_name).stem}_{uuid4().hex[:8]}.csv"
    result.dataframe.to_csv(destination, index=False, encoding="utf-8")
    return MetadataCompletionResult(
        dataframe=result.dataframe,
        changes=result.changes,
        output_path=str(destination),
        source_dataframe=result.source_dataframe,
    )


def metadata_completion_changes_to_dataframe(
    changes: Iterable[MetadataCompletionChange],
) -> pd.DataFrame:
    """Convert completion changes to a human-review-friendly dataframe."""
    rows = []
    for change in changes:
        candidates = change.candidate_values or [change.completed_value]
        rows.append(
            {
                "object_type": change.object_type,
                "change_key": completion_change_key(change),
                "table_name": change.table_name,
                "field_name": change.field_name,
                "column_name": change.column_name,
                "original_value": change.original_value,
                "completed_value": change.completed_value,
                "candidate_1": candidates[0] if len(candidates) > 0 else "",
                "candidate_2": candidates[1] if len(candidates) > 1 else "",
                "candidate_3": candidates[2] if len(candidates) > 2 else "",
                "final_value": change.completed_value,
                "confidence": change.confidence,
                "source": change.source,
                "evidence_joined": " | ".join(change.evidence),
            }
        )
    return pd.DataFrame(rows)
