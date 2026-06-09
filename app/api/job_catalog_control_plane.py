"""Control-plane entries for the jobs catalog."""

CONTROL_PLANE_JOB_ITEMS = [
    {
        "name": "list_config_assets",
        "method": "GET",
        "path": "/jobs/config-assets",
        "description": "Return managed governance configuration assets from the local control plane.",
    },
    {
        "name": "get_config_asset",
        "method": "GET",
        "path": "/jobs/config-assets/{asset_name}",
        "description": "Return one managed governance configuration asset and its current content.",
    },
    {
        "name": "validate_config_asset",
        "method": "POST",
        "path": "/jobs/config-assets/{asset_name}/validate",
        "description": "Validate one managed governance configuration asset.",
    },
    {
        "name": "save_config_asset",
        "method": "POST",
        "path": "/jobs/config-assets/{asset_name}/save",
        "description": "Save one managed governance configuration asset after validation.",
    },
    {
        "name": "publish_config_asset",
        "method": "POST",
        "path": "/jobs/config-assets/{asset_name}/publish",
        "description": "Mark one managed governance configuration asset as published.",
    },
    {
        "name": "learning_health",
        "method": "GET",
        "path": "/jobs/learning-health",
        "description": "Return local learning-memory health summary for maintenance.",
    },
    {
        "name": "learning_health_details",
        "method": "GET",
        "path": "/jobs/learning-health/details",
        "description": "Return learned-memory conflict, generic, and invalid record details.",
    },
    {
        "name": "learning_maintenance_report",
        "method": "GET",
        "path": "/jobs/learning-health/report",
        "description": "Return a consolidated learning-memory maintenance report with health, backup validation, and recommended actions.",
    },
    {
        "name": "export_learning_maintenance_report",
        "method": "POST",
        "path": "/jobs/learning-health/report/export",
        "description": "Export the consolidated learning-memory maintenance report as JSON and Markdown files.",
    },
    {
        "name": "create_learning_memory_backup",
        "method": "POST",
        "path": "/jobs/learning-health/backups",
        "description": "Create a timestamped local backup package for learning-memory files.",
    },
    {
        "name": "list_learning_memory_backups",
        "method": "GET",
        "path": "/jobs/learning-health/backups",
        "description": "Return local learning-memory backup packages, newest first.",
    },
    {
        "name": "restore_learning_memory_backup",
        "method": "POST",
        "path": "/jobs/learning-health/backups/restore",
        "description": "Restore local learning-memory files from one backup package.",
    },
    {
        "name": "validate_learning_memory_backup",
        "method": "POST",
        "path": "/jobs/learning-health/backups/validate",
        "description": "Validate one local learning-memory backup package before restore.",
    },
    {
        "name": "prune_invalid_learning_memory",
        "method": "POST",
        "path": "/jobs/learning-health/prune-invalid",
        "description": "Remove clearly invalid mapping, STG, and metadata completion learning records from local stores.",
    },
    {
        "name": "backup_then_prune_invalid_learning_memory",
        "method": "POST",
        "path": "/jobs/learning-health/backup-then-prune-invalid",
        "description": "Create a learning-memory backup before removing invalid records from local stores.",
    },
    {
        "name": "clear_learning_memory_field_key",
        "method": "POST",
        "path": "/jobs/learning-health/clear-field-key",
        "description": "Clear learned-memory records for one field key in one memory domain: standard_mapping, stg_standardization, or metadata_completion.",
    },
]
