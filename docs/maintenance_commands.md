# Maintenance Commands

This project includes a small command-line maintenance entrypoint for routine local checks.

## Validate Managed Configuration

Run this after editing workflow profiles, project templates, domain packs, rule templates, dictionaries, standards, or workbook mappings:

```powershell
python -m app.maintenance validate-config
```

The command validates all assets registered in `app/data/control_plane/asset_registry.json`.
It is read-only and does not update `app/data/control_plane/config_status.json`, so it is safe to run before commits.

Expected healthy output:

```text
Configuration asset validation
Checked 36 assets: 36 valid, 0 invalid, 0 warnings.
```

If an asset is invalid, fix the listed error before running the app or exporting delivery artifacts.

## Run Platform Doctor

Run this before a commit or after changing tool registry, project templates, workflow profiles, or domain packs:

```powershell
python -m app.maintenance doctor
```

This includes the configuration validation above, then checks cross-file platform consistency:

- enabled tools point to registered executor handlers
- enabled project templates reference existing workflow profiles
- project template default domain packs exist
- domain delivery defaults reference existing domain packs

Expected healthy output:

```text
Platform consistency checks
[OK] tool handlers
[OK] project template references
[OK] domain delivery references
```

## Suggested Daily Loop

```powershell
python -m app.maintenance doctor
python -m pytest -q
git status
```

Use the Miniconda Python interpreter directly if your default `python` does not have the project dependencies installed.
