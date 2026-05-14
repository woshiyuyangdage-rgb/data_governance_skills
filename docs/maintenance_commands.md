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

## Run Quick Check

Run this before small commits when you want a faster confidence pass than the full suite:

```powershell
python -m app.maintenance quick-check
```

The command runs `doctor` first, then runs a focused pytest set around configuration loading,
the control plane, tool registration, project templates, and domain packs. If `doctor` fails,
the test step is skipped so the first configuration problem stays visible.

Use the full test suite before larger changes:

```powershell
python -m pytest -q
```

## Show Common Commands

Print the daily command cheat sheet from the same maintenance entrypoint:

```powershell
python -m app.maintenance commands
```

## Suggested Daily Loop

```powershell
python -m app.maintenance quick-check
git status
```

Use the Miniconda Python interpreter directly if your default `python` does not have the project dependencies installed.
