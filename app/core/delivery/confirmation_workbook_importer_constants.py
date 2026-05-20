"""Shared constants for confirmation workbook import flows."""

REQUIRED_COLUMNS = {
    "mapping_confirmation": [
        "source_table_name",
        "source_field_name",
        "confirmation_status",
    ],
    "stg_confirmation": [
        "source_table_name",
        "source_field_name",
        "confirmation_status",
    ],
    "quality_rule_confirmation": [
        "source_table_name",
        "rule_type",
        "confirmation_status",
    ],
    "backlog_confirmation": [
        "backlog_id",
        "confirmation_status",
    ],
}
