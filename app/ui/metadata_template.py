"""Metadata template download helpers for the Streamlit UI."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

METADATA_TEMPLATE_COLUMNS: list[tuple[str, str]] = [
    ("table_name", "表英文名 / table_name"),
    ("table_name_cn", "表中文名 / table_name_cn"),
    ("table_description", "表描述 / table_description"),
    ("schema_name", "所属schema / schema_name"),
    ("system_name", "来源系统 / system_name"),
    ("business_domain", "业务域 / business_domain"),
    ("owner_role", "责任角色 / owner_role"),
    ("lifecycle_status", "生命周期状态 / lifecycle_status"),
    ("data_layer", "数据分层 / data_layer"),
    ("field_name", "字段英文名 / field_name"),
    ("field_name_cn", "字段中文名 / field_name_cn"),
    ("field_description", "字段描述 / field_description"),
    ("data_type", "数据类型 / data_type"),
    ("data_length", "数据长度 / data_length"),
    ("sample_values", "样例值 / sample_values"),
    ("nullable", "是否可空 / nullable"),
    ("field_standard_code", "字段标准编码 / field_standard_code"),
    ("field_standard_name", "字段标准名称 / field_standard_name"),
    ("is_primary_key", "是否主键 / is_primary_key"),
    ("is_foreign_key", "是否外键 / is_foreign_key"),
    ("is_sensitive", "是否敏感 / is_sensitive"),
]

METADATA_TEMPLATE_SAMPLE_ROWS: list[dict[str, object]] = [
    {
        "table_name": "customer_master",
        "table_name_cn": "客户主数据",
        "table_description": "记录客户基础信息和客户统一标识。",
        "schema_name": "dim",
        "system_name": "crm",
        "business_domain": "客户域",
        "owner_role": "客户数据负责人",
        "lifecycle_status": "active",
        "data_layer": "dim",
        "field_name": "customer_id",
        "field_name_cn": "客户编号",
        "field_description": "客户在企业内部的唯一识别编号。",
        "data_type": "varchar",
        "data_length": "64",
        "sample_values": "C10001;C10002",
        "nullable": "false",
        "field_standard_code": "STD_CUST_ID",
        "field_standard_name": "客户编号",
        "is_primary_key": "true",
        "is_foreign_key": "false",
        "is_sensitive": "false",
    },
    {
        "table_name": "contract_info",
        "table_name_cn": "合同信息",
        "table_description": "记录融资合同的基础信息和状态。",
        "schema_name": "ods",
        "system_name": "loan",
        "business_domain": "融资域",
        "owner_role": "合同数据负责人",
        "lifecycle_status": "active",
        "data_layer": "ods",
        "field_name": "contract_no",
        "field_name_cn": "合同编号",
        "field_description": "融资合同的唯一业务编号。",
        "data_type": "varchar",
        "data_length": "80",
        "sample_values": "HT20260001;HT20260002",
        "nullable": "false",
        "field_standard_code": "STD_CONTRACT_NO",
        "field_standard_name": "合同编号",
        "is_primary_key": "true",
        "is_foreign_key": "false",
        "is_sensitive": "false",
    },
    {
        "table_name": "contract_info",
        "table_name_cn": "合同信息",
        "table_description": "记录融资合同的基础信息和状态。",
        "schema_name": "ods",
        "system_name": "loan",
        "business_domain": "融资域",
        "owner_role": "合同数据负责人",
        "lifecycle_status": "active",
        "data_layer": "ods",
        "field_name": "contract_amt",
        "field_name_cn": "合同金额",
        "field_description": "融资合同约定的合同金额，通常以人民币为单位。",
        "data_type": "decimal",
        "data_length": "18,2",
        "sample_values": "100000.00;250000.00",
        "nullable": "false",
        "field_standard_code": "STD_CONTRACT_AMT",
        "field_standard_name": "合同金额",
        "is_primary_key": "false",
        "is_foreign_key": "false",
        "is_sensitive": "false",
    },
]

METADATA_TEMPLATE_FORMAT_OPTIONS = {
    "CSV": {
        "extension": "csv",
        "mime": "text/csv",
    },
    "Excel": {
        "extension": "xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
}


def build_metadata_template_dataframe() -> pd.DataFrame:
    """Return the bilingual metadata template with starter rows."""
    canonical_columns = [column for column, _ in METADATA_TEMPLATE_COLUMNS]
    display_columns = [label for _, label in METADATA_TEMPLATE_COLUMNS]
    dataframe = pd.DataFrame(METADATA_TEMPLATE_SAMPLE_ROWS, columns=canonical_columns)
    dataframe.columns = display_columns
    return dataframe


def build_metadata_template_file(format_name: str) -> tuple[bytes, str, str]:
    """Return template bytes, file name, and mime for a selected format."""
    normalized_format = format_name if format_name in METADATA_TEMPLATE_FORMAT_OPTIONS else "CSV"
    template_dataframe = build_metadata_template_dataframe()
    option = METADATA_TEMPLATE_FORMAT_OPTIONS[normalized_format]
    extension = str(option["extension"])
    mime = str(option["mime"])

    if extension == "xlsx":
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            template_dataframe.to_excel(writer, index=False, sheet_name="metadata_template")
        return (
            buffer.getvalue(),
            "metadata_input_template.xlsx",
            mime,
        )

    return (
        template_dataframe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        "metadata_input_template.csv",
        mime,
    )


def render_metadata_template_download(
    *,
    key_prefix: str,
    button_label: str = "下载元数据模板",
) -> None:
    """Render a format selector and metadata template download button."""
    format_name = st.selectbox(
        "模板格式",
        list(METADATA_TEMPLATE_FORMAT_OPTIONS.keys()),
        key=f"{key_prefix}_metadata_template_format",
        label_visibility="collapsed",
    )
    file_bytes, file_name, mime = build_metadata_template_file(format_name)
    st.download_button(
        label=button_label,
        data=file_bytes,
        file_name=file_name,
        mime=mime,
        use_container_width=True,
        key=f"{key_prefix}_metadata_template_download",
    )
