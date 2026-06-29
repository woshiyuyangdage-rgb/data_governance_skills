"""Command-line maintenance helpers for local project operation."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

QUICK_CHECK_TEST_TARGETS = (
    "tests/test_maintenance.py",
    "tests/test_control_plane_service.py",
    "tests/test_tool_loader.py",
    "tests/test_tool_service.py",
    "tests/test_governance_tool_executor.py",
    "tests/test_agent_shell_service.py",
    "tests/test_schema_exporter.py",
    "tests/test_routes_jobs_tools.py",
    "tests/test_project_template_loader.py",
    "tests/test_domain_pack_loader.py",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_ARTIFACT_NAMES = {"__pycache__", ".pytest_cache", ".ruff_cache"}
CLEAN_ARTIFACT_PREFIXES = ("pytest-cache-files-", ".pytest_runtime", "pytest_tmp")

COMMON_COMMAND_GROUPS = (
    (
        "Daily checks",
        (
            ("Validate config", "python -m app.maintenance validate-config"),
            ("Platform doctor", "python -m app.maintenance doctor"),
            ("Quick check", "python -m app.maintenance quick-check"),
            ("Clean local artifacts", "python -m app.maintenance clean-local-artifacts"),
            ("Full tests", "python -m pytest -q"),
        ),
    ),
    (
        "Local app",
        (
            ("FastAPI", "python -m uvicorn app.main:app --reload"),
            ("Streamlit", "python -m streamlit run app/ui/streamlit_app.py"),
        ),
    ),
    (
        "Git",
        (
            ("Status", "git status --short --branch"),
            ("Push", "git push"),
        ),
    ),
)


def _format_validation_result(result: Any) -> list[str]:
    status = "OK" if result.is_valid else "FAIL"
    lines = [f"[{status}] {result.asset_name}"]
    for message in result.messages:
        lines.append(f"  error: {message}")
    for warning in result.warnings:
        lines.append(f"  warning: {warning}")
    return lines


def validate_config_assets() -> int:
    """Validate all managed governance configuration assets."""
    service = _build_control_plane_service()
    results = service.validate_all_assets(persist_status=False)
    valid_count = sum(1 for result in results if result.is_valid)
    warning_count = sum(len(result.warnings) for result in results)
    failure_count = len(results) - valid_count

    print("Configuration asset validation")
    print(
        f"Checked {len(results)} assets: "
        f"{valid_count} valid, {failure_count} invalid, {warning_count} warnings."
    )
    for result in results:
        if result.is_valid and not result.warnings:
            continue
        for line in _format_validation_result(result):
            print(line)

    return 0 if failure_count == 0 else 1


def _check_tool_handlers() -> list[str]:
    executor = _build_governance_tool_executor()
    registered_handlers = executor.list_registered_handler_names()
    schema_names, tool_examples = _load_schema_export_contracts()
    seen_tool_names: set[str] = set()
    errors: list[str] = []
    for tool in _load_tool_registry():
        if tool.name in seen_tool_names:
            errors.append(f"tool registry contains duplicate tool name '{tool.name}'")
        seen_tool_names.add(tool.name)

        if tool.enabled and tool.handler not in registered_handlers:
            errors.append(
                f"tool '{tool.name}' references unregistered handler '{tool.handler}'"
            )
        if tool.input_model not in schema_names:
            errors.append(
                f"tool '{tool.name}' references missing input schema "
                f"'{tool.input_model}'"
            )
        if tool.output_model not in schema_names:
            errors.append(
                f"tool '{tool.name}' references missing output schema "
                f"'{tool.output_model}'"
            )

    for tool_name, examples in tool_examples.items():
        if tool_name not in seen_tool_names:
            errors.append(f"tool examples reference missing tool '{tool_name}'")
        if not isinstance(examples, list):
            errors.append(f"tool examples for '{tool_name}' must be a list")
            continue
        for index, example in enumerate(examples):
            if not isinstance(example, dict):
                errors.append(
                    f"tool example {index} for '{tool_name}' must be a mapping"
                )
    return errors


def _check_project_template_references() -> list[str]:
    profile_names = {profile.name for profile in _list_enabled_profiles()}
    domain_pack_names = {pack.pack_name for pack in _list_enabled_domain_packs()}
    errors: list[str] = []
    for template in _list_enabled_project_templates():
        if template.base_workflow_profile not in profile_names:
            errors.append(
                f"project template '{template.template_name}' references missing "
                f"workflow profile '{template.base_workflow_profile}'"
            )
        if (
            template.default_domain_pack
            and template.default_domain_pack not in domain_pack_names
        ):
            errors.append(
                f"project template '{template.template_name}' references missing "
                f"domain pack '{template.default_domain_pack}'"
            )
    return errors


def _check_domain_delivery_references() -> list[str]:
    domain_pack_names = {pack.pack_name for pack in _list_enabled_domain_packs()}
    defaults = _get_domain_delivery_templates_config().get("delivery_defaults", {})
    errors: list[str] = []
    if not isinstance(defaults, dict):
        return ["domain delivery defaults must be a mapping"]
    for domain_pack_name in defaults:
        if domain_pack_name not in domain_pack_names:
            errors.append(
                f"domain delivery defaults reference missing domain pack "
                f"'{domain_pack_name}'"
            )
    return errors


def _build_control_plane_service() -> Any:
    from app.core.control_plane import ControlPlaneService

    return ControlPlaneService()


def _build_governance_tool_executor() -> Any:
    from app.core.tools.governance_tool_executor import GovernanceToolExecutor

    return GovernanceToolExecutor()


def _load_tool_registry() -> list[Any]:
    from app.core.tools.tool_loader import load_tool_registry

    return load_tool_registry()


def _load_schema_export_contracts() -> tuple[set[str], dict[str, Any]]:
    from app.core.adapters.schema_export_definitions import (
        MODEL_SCHEMA_MAP,
        TOOL_EXAMPLES,
    )

    return set(MODEL_SCHEMA_MAP), dict(TOOL_EXAMPLES)


def _list_enabled_profiles() -> list[Any]:
    from app.core.orchestrator.profile_loader import list_enabled_profiles

    return list_enabled_profiles()


def _list_enabled_domain_packs() -> list[Any]:
    from app.core.domain.domain_pack_loader import list_enabled_domain_packs

    return list_enabled_domain_packs()


def _list_enabled_project_templates() -> list[Any]:
    from app.core.templates.project_template_loader import (
        list_enabled_project_templates,
    )

    return list_enabled_project_templates()


def _get_domain_delivery_templates_config() -> dict[str, Any]:
    from app.core.rules.config_loader import get_domain_delivery_templates_config

    return get_domain_delivery_templates_config()


def run_platform_doctor() -> int:
    """Run platform-level consistency checks for routine maintenance."""
    validation_exit_code = validate_config_assets()
    checks = {
        "tool handlers": _check_tool_handlers(),
        "project template references": _check_project_template_references(),
        "domain delivery references": _check_domain_delivery_references(),
    }

    print()
    print("Platform consistency checks")
    failure_count = 0
    for check_name, errors in checks.items():
        if not errors:
            print(f"[OK] {check_name}")
            continue
        failure_count += len(errors)
        print(f"[FAIL] {check_name}")
        for error in errors:
            print(f"  error: {error}")

    return 0 if validation_exit_code == 0 and failure_count == 0 else 1


def print_common_commands() -> int:
    """Print the commands used most often while operating the local platform."""
    print("Common local commands", flush=True)
    for group_name, commands in COMMON_COMMAND_GROUPS:
        print(flush=True)
        print(group_name, flush=True)
        for label, command in commands:
            print(f"  {label}: {command}", flush=True)
    return 0


def _run_subprocess(command: Sequence[str]) -> int:
    print(flush=True)
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def run_quick_check(test_targets: Sequence[str] = QUICK_CHECK_TEST_TARGETS) -> int:
    """Run the fastest useful local confidence checks before a commit."""
    print("Quick check", flush=True)
    print("Runs platform doctor and focused maintenance tests.", flush=True)
    doctor_exit_code = run_platform_doctor()
    if doctor_exit_code != 0:
        print(flush=True)
        print("Quick check stopped because platform doctor failed.", flush=True)
        return doctor_exit_code

    pytest_command = [sys.executable, "-B", "-m", "pytest", "-q", *test_targets]
    return _run_subprocess(pytest_command)


def _is_cleanable_artifact(path: Path) -> bool:
    name = path.name
    return name in CLEAN_ARTIFACT_NAMES or any(
        name.startswith(prefix) for prefix in CLEAN_ARTIFACT_PREFIXES
    )


def _iter_project_directories_bottom_up() -> list[Path]:
    directories: list[Path] = []
    for root, dirnames, _ in os.walk(PROJECT_ROOT, onerror=lambda _error: None):
        root_path = Path(root)
        directories.extend(root_path / dirname for dirname in dirnames)
    return sorted(directories, key=lambda item: len(item.parts), reverse=True)


def clean_local_artifacts() -> int:
    """Remove local Python and pytest cache artifacts from the project tree."""
    removed: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    for path in _iter_project_directories_bottom_up():
        if not _is_cleanable_artifact(path):
            continue
        try:
            shutil.rmtree(path)
        except OSError as exc:
            skipped.append((path.relative_to(PROJECT_ROOT), str(exc)))
            continue
        removed.append(path.relative_to(PROJECT_ROOT))

    print("Local artifact cleanup")
    if not removed and not skipped:
        print("No local cache artifacts found.")
        return 0

    if removed:
        print(f"Removed {len(removed)} directories:")
        for path in removed:
            print(f"  {path}")
    if skipped:
        print(f"Skipped {len(skipped)} directories:")
        for path, reason in skipped:
            print(f"  {path}: {reason}")
    return 1 if skipped else 0


def build_parser() -> argparse.ArgumentParser:
    """Build the maintenance command parser."""
    parser = argparse.ArgumentParser(
        prog="python -m app.maintenance",
        description="Local maintenance commands for the governance assistant platform.",
    )
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate all managed YAML, JSON, and CSV governance assets.",
    )
    validate_parser.set_defaults(handler=lambda _args: validate_config_assets())

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run config validation plus platform consistency checks.",
    )
    doctor_parser.set_defaults(handler=lambda _args: run_platform_doctor())

    quick_check_parser = subparsers.add_parser(
        "quick-check",
        help="Run platform doctor plus focused maintenance tests.",
    )
    quick_check_parser.set_defaults(handler=lambda _args: run_quick_check())

    clean_parser = subparsers.add_parser(
        "clean-local-artifacts",
        help="Remove local __pycache__, .pytest_cache, and pytest temporary cache directories.",
    )
    clean_parser.set_defaults(handler=lambda _args: clean_local_artifacts())

    commands_parser = subparsers.add_parser(
        "commands",
        help="Print common local development and maintenance commands.",
    )
    commands_parser.set_defaults(handler=lambda _args: print_common_commands())

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a maintenance command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
