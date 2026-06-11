"""Tests for command-line maintenance helpers."""

from app import maintenance
from app.core.models.validation_result import ValidationResult


class _FakeControlPlaneService:
    results: list[ValidationResult] = []
    persist_status: bool | None = None

    def validate_all_assets(self, *, persist_status: bool = True) -> list[ValidationResult]:
        type(self).persist_status = persist_status
        return list(self.results)


class _FakeTool:
    def __init__(
        self,
        name: str,
        handler: str,
        enabled: bool = True,
        input_model: str = "dict",
        output_model: str = "dict",
    ) -> None:
        self.name = name
        self.handler = handler
        self.enabled = enabled
        self.input_model = input_model
        self.output_model = output_model


class _FakeExecutor:
    handler_names: set[str] = set()

    def list_registered_handler_names(self) -> set[str]:
        return set(self.handler_names)


class _FakeProfile:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeDomainPack:
    def __init__(self, pack_name: str) -> None:
        self.pack_name = pack_name


class _FakeTemplate:
    def __init__(
        self,
        template_name: str,
        base_workflow_profile: str,
        default_domain_pack: str | None = None,
    ) -> None:
        self.template_name = template_name
        self.base_workflow_profile = base_workflow_profile
        self.default_domain_pack = default_domain_pack


def test_validate_config_assets_returns_success_for_valid_assets(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        maintenance,
        "_build_control_plane_service",
        lambda: _FakeControlPlaneService(),
    )
    _FakeControlPlaneService.results = [
        ValidationResult(asset_name="workflow_profiles", is_valid=True),
        ValidationResult(
            asset_name="intent_patterns",
            is_valid=True,
            warnings=["contains a weak keyword match"],
        ),
    ]

    exit_code = maintenance.validate_config_assets()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert _FakeControlPlaneService.persist_status is False
    assert "2 valid, 0 invalid, 1 warnings" in captured.out
    assert "[OK] intent_patterns" in captured.out
    assert "warning: contains a weak keyword match" in captured.out


def test_validate_config_assets_returns_failure_for_invalid_assets(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        maintenance,
        "_build_control_plane_service",
        lambda: _FakeControlPlaneService(),
    )
    _FakeControlPlaneService.results = [
        ValidationResult(asset_name="workflow_profiles", is_valid=True),
        ValidationResult(
            asset_name="tool_registry",
            is_valid=False,
            messages=["tool names must be unique"],
        ),
    ]

    exit_code = maintenance.validate_config_assets()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "1 valid, 1 invalid, 0 warnings" in captured.out
    assert "[FAIL] tool_registry" in captured.out
    assert "error: tool names must be unique" in captured.out


def test_maintenance_main_without_command_prints_help(capsys) -> None:
    exit_code = maintenance.main([])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "validate-config" in captured.out
    assert "quick-check" in captured.out
    assert "commands" in captured.out


def test_quick_check_targets_include_tool_contract_checks() -> None:
    targets = set(maintenance.QUICK_CHECK_TEST_TARGETS)

    assert "tests/test_tool_loader.py" in targets
    assert "tests/test_tool_service.py" in targets
    assert "tests/test_agent_shell_service.py" in targets
    assert "tests/test_schema_exporter.py" in targets
    assert "tests/test_routes_jobs_tools.py" in targets


def test_tool_handler_check_reports_unregistered_enabled_handler(monkeypatch) -> None:
    monkeypatch.setattr(
        maintenance,
        "_build_governance_tool_executor",
        lambda: _FakeExecutor(),
    )
    monkeypatch.setattr(
        maintenance,
        "_load_tool_registry",
        lambda: [
            _FakeTool(
                "known_tool",
                "governance_tool_executor.known_tool",
            ),
            _FakeTool(
                "missing_tool",
                "governance_tool_executor.missing_tool",
            ),
            _FakeTool(
                "disabled_tool",
                "governance_tool_executor.disabled_tool",
                enabled=False,
            ),
        ],
    )
    monkeypatch.setattr(
        maintenance,
        "_load_schema_export_contracts",
        lambda: ({"dict"}, {}),
    )
    _FakeExecutor.handler_names = {"governance_tool_executor.known_tool"}

    errors = maintenance._check_tool_handlers()

    assert errors == [
        "tool 'missing_tool' references unregistered handler "
        "'governance_tool_executor.missing_tool'"
    ]


def test_tool_handler_check_reports_schema_and_example_contract_issues(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        maintenance,
        "_build_governance_tool_executor",
        lambda: _FakeExecutor(),
    )
    monkeypatch.setattr(
        maintenance,
        "_load_tool_registry",
        lambda: [
            _FakeTool(
                "known_tool",
                "governance_tool_executor.known_tool",
                input_model="KnownInput",
                output_model="KnownOutput",
            ),
            _FakeTool(
                "known_tool",
                "governance_tool_executor.known_tool",
                input_model="MissingInput",
                output_model="MissingOutput",
            ),
        ],
    )
    monkeypatch.setattr(
        maintenance,
        "_load_schema_export_contracts",
        lambda: (
            {"KnownInput", "KnownOutput"},
            {
                "known_tool": [{"ok": True}, "bad_example"],
                "missing_tool": [{"ok": True}],
                "malformed_examples": {"not": "a list"},
            },
        ),
    )
    _FakeExecutor.handler_names = {"governance_tool_executor.known_tool"}

    errors = maintenance._check_tool_handlers()

    assert errors == [
        "tool registry contains duplicate tool name 'known_tool'",
        "tool 'known_tool' references missing input schema 'MissingInput'",
        "tool 'known_tool' references missing output schema 'MissingOutput'",
        "tool example 1 for 'known_tool' must be a mapping",
        "tool examples reference missing tool 'missing_tool'",
        "tool examples reference missing tool 'malformed_examples'",
        "tool examples for 'malformed_examples' must be a list",
    ]


def test_project_template_reference_check_reports_missing_links(monkeypatch) -> None:
    monkeypatch.setattr(
        maintenance,
        "_list_enabled_profiles",
        lambda: [_FakeProfile("metadata_diagnosis_only")],
    )
    monkeypatch.setattr(
        maintenance,
        "_list_enabled_domain_packs",
        lambda: [_FakeDomainPack("customer_domain_pack")],
    )
    monkeypatch.setattr(
        maintenance,
        "_list_enabled_project_templates",
        lambda: [
            _FakeTemplate(
                "broken_template",
                "missing_profile",
                "missing_domain_pack",
            )
        ],
    )

    errors = maintenance._check_project_template_references()

    assert errors == [
        "project template 'broken_template' references missing workflow profile "
        "'missing_profile'",
        "project template 'broken_template' references missing domain pack "
        "'missing_domain_pack'",
    ]


def test_domain_delivery_reference_check_reports_missing_pack(monkeypatch) -> None:
    monkeypatch.setattr(
        maintenance,
        "_list_enabled_domain_packs",
        lambda: [_FakeDomainPack("customer_domain_pack")],
    )
    monkeypatch.setattr(
        maintenance,
        "_get_domain_delivery_templates_config",
        lambda: {
            "delivery_defaults": {
                "customer_domain_pack": {"include_outputs": ["mapping_report"]},
                "missing_domain_pack": {"include_outputs": ["quality_report"]},
            }
        },
    )

    errors = maintenance._check_domain_delivery_references()

    assert errors == [
        "domain delivery defaults reference missing domain pack 'missing_domain_pack'"
    ]


def test_print_common_commands_lists_daily_operations(capsys) -> None:
    exit_code = maintenance.print_common_commands()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Common local commands" in captured.out
    assert "python -m app.maintenance doctor" in captured.out
    assert "python -m app.maintenance quick-check" in captured.out
    assert "python -m pytest -q" in captured.out


def test_quick_check_runs_doctor_then_focused_tests(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(maintenance, "run_platform_doctor", lambda: 0)
    monkeypatch.setattr(
        maintenance,
        "_run_subprocess",
        lambda command: calls.append(tuple(command)) or 0,
    )

    exit_code = maintenance.run_quick_check(["tests/test_maintenance.py"])

    assert exit_code == 0
    assert calls == [
        (
            maintenance.sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_maintenance.py",
        )
    ]


def test_quick_check_stops_when_doctor_fails(monkeypatch, capsys) -> None:
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(maintenance, "run_platform_doctor", lambda: 1)
    monkeypatch.setattr(
        maintenance,
        "_run_subprocess",
        lambda command: calls.append(tuple(command)) or 0,
    )

    exit_code = maintenance.run_quick_check(["tests/test_maintenance.py"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert calls == []
    assert "platform doctor failed" in captured.out
