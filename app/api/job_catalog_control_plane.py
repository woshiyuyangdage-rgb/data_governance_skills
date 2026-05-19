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
]
