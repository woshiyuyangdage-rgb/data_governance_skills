"""Command-line maintenance helpers for local project operation."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.core.control_plane import ControlPlaneService
from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.models.validation_result import ValidationResult
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.rules.config_loader import get_domain_delivery_templates_config
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.tools.governance_tool_executor import GovernanceToolExecutor
from app.core.tools.tool_loader import load_tool_registry


def _format_validation_result(result: ValidationResult) -> list[str]:
    status = "OK" if result.is_valid else "FAIL"
    lines = [f"[{status}] {result.asset_name}"]
    for message in result.messages:
        lines.append(f"  error: {message}")
    for warning in result.warnings:
        lines.append(f"  warning: {warning}")
    return lines


def validate_config_assets() -> int:
    """Validate all managed governance configuration assets."""
    service = ControlPlaneService()
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
    executor = GovernanceToolExecutor()
    registered_handlers = executor.list_registered_handler_names()
    errors: list[str] = []
    for tool in load_tool_registry():
        if tool.enabled and tool.handler not in registered_handlers:
            errors.append(
                f"tool '{tool.name}' references unregistered handler '{tool.handler}'"
            )
    return errors


def _check_project_template_references() -> list[str]:
    profile_names = {profile.name for profile in list_enabled_profiles()}
    domain_pack_names = {pack.pack_name for pack in list_enabled_domain_packs()}
    errors: list[str] = []
    for template in list_enabled_project_templates():
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
    domain_pack_names = {pack.pack_name for pack in list_enabled_domain_packs()}
    defaults = get_domain_delivery_templates_config().get("delivery_defaults", {})
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
