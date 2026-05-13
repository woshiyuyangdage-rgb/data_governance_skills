"""Shared demo dataset for the rule-based P0 pipeline."""

from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta


def build_demo_tables() -> list[TableMeta]:
    """Return representative demo tables with varied governance issues."""
    return [
        TableMeta(
            table_name="ods_customer_snapshot",
            table_name_cn="客户快照表",
            table_description=None,
            schema_name="ods",
            system_name="crm",
            fields=[
                FieldMeta(
                    field_name="customer_id",
                    field_name_cn="客户ID",
                    field_description="Customer identifier",
                    data_type="string",
                    nullable=False,
                ),
                FieldMeta(
                    field_name="snapshot_dt",
                    field_name_cn=None,
                    field_description=None,
                    data_type="date",
                    nullable=False,
                ),
            ],
        ),
        TableMeta(
            table_name="Sales Order Header",
            table_name_cn="销售订单头",
            table_description="单",
            schema_name="mart",
            system_name="erp",
            fields=[
                FieldMeta(
                    field_name="Order__ID",
                    field_name_cn="订单ID",
                    field_description="ID",
                    data_type="string",
                    nullable=False,
                ),
                FieldMeta(
                    field_name="Cust ID",
                    field_name_cn=None,
                    field_description="客户",
                    data_type="string",
                    nullable=True,
                ),
            ],
        ),
        TableMeta(
            table_name="user_audit_log",
            table_name_cn="用户审计日志表",
            table_description="日志表",
            schema_name="ops",
            system_name="security",
            fields=[
                FieldMeta(
                    field_name="log_id",
                    field_name_cn=None,
                    field_description="日志ID",
                    data_type="string",
                    nullable=False,
                ),
                FieldMeta(
                    field_name="event_trace_code",
                    field_name_cn=None,
                    field_description="trace",
                    data_type="string",
                    nullable=False,
                ),
            ],
        ),
        TableMeta(
            table_name="customer_master",
            table_name_cn="客户主数据",
            table_description="Customer master table for active customers.",
            schema_name="dim",
            system_name="crm",
            fields=[
                FieldMeta(
                    field_name="customer_id",
                    field_name_cn="客户ID",
                    field_description="Unique customer identifier.",
                    data_type="string",
                    nullable=False,
                ),
                FieldMeta(
                    field_name="customer_name",
                    field_name_cn="客户名称",
                    field_description="Official customer display name.",
                    data_type="string",
                    nullable=False,
                ),
            ],
        ),
    ]
