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
Checked 38 assets: 38 valid, 0 invalid, 0 warnings.
```

If an asset is invalid, fix the listed error before running the app or exporting delivery artifacts.

## Run Platform Doctor

Run this before a commit or after changing tool registry, project templates, workflow profiles, or domain packs:

```powershell
python -m app.maintenance doctor
```

This includes the configuration validation above, then checks cross-file platform consistency:

- `pyproject.toml` version matches the FastAPI application version
- development-only dependencies stay out of `requirements.txt`
- enabled tools point to registered executor handlers
- enabled project templates reference existing workflow profiles
- project template default domain packs exist
- domain delivery defaults reference existing domain packs

Expected healthy output:

```text
Platform consistency checks
[OK] version consistency
[OK] dependency layering
[OK] tool handlers
[OK] project template references
[OK] domain delivery references
```

## Check Workspace Hygiene

Run this when recursive scans, Git status, or local tests seem slow or noisy:

```powershell
python -m app.maintenance workspace-hygiene
```

The command reports local runtime artifact volume and filesystem access warnings.
It is read-only; it does not delete traces, reports, cache directories, or pytest
temporary folders. A non-zero exit code means at least one local artifact path could
not be read and should be cleaned up or fixed manually.

## Clean Local Artifacts

Run this after tests create many local cache directories or `workspace-hygiene`
reports pytest temporary folders:

```powershell
python -m app.maintenance clean-local-artifacts
```

The cleanup command removes project-local Python caches, pytest caches, Ruff
caches, `.pytest_runtime*`, `pytest_parent*`, and `pytest_tmp*` directories. It
intentionally skips isolated dependency and VCS roots such as `.venv`, `venv`,
`.git`, and `node_modules`.

If ACL-protected pytest leftovers cannot be removed, the command returns a
non-zero exit code and lists the skipped paths. Verify each path is under the
project root, then remove it from an elevated/admin PowerShell session or fix the
directory ownership and permissions.

## Local Path Boundaries

Local metadata input paths and generated delivery output directories are constrained
to project-safe roots by default. This keeps the FastAPI and Streamlit entrypoints
usable as a local single-user tool without silently accepting arbitrary filesystem
paths.

To allow an additional trusted root outside the project tree, set:

```powershell
$env:DATA_GOVERNANCE_ALLOWED_LOCAL_ROOTS = "D:\trusted-metadata"
```

Use `;` between multiple roots on Windows and `:` on Unix-like systems.

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
python -m ruff check app tests
python -m app.maintenance doctor
python -m pytest -q
```

## Continuous Integration

GitHub Actions runs the repository checks on pull requests, pushes to `main`, and
manual workflow dispatches. The CI matrix currently covers Python 3.10 and 3.13.

The CI job installs `requirements-dev.txt`, then runs:

```powershell
python -m ruff check app tests
python -m app.maintenance doctor
python -m pytest -q
```

Keep local checks aligned with `.github/workflows/ci.yml` when adding new quality
gates.

## Show Common Commands

Print the daily command cheat sheet from the same maintenance entrypoint:

```powershell
python -m app.maintenance commands
```

## Suggested Daily Loop

```powershell
python -m app.maintenance workspace-hygiene
python -m app.maintenance quick-check
git status
```

Install runtime dependencies with `requirements.txt`, and install local development
dependencies with `requirements-dev.txt`. Use the Miniconda Python interpreter
directly if your default `python` does not have the project dependencies installed.
