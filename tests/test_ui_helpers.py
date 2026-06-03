"""Tests for lightweight Streamlit UI helper logic."""

from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager

from app.ui.control_plane_helpers import (
    can_publish_without_save,
    content_fingerprint,
    diff_stats,
    should_warn_baseline_changed,
)
from app.ui import page_utils
from app.ui import performance_helpers
from app.ui.column_labels import localize_dataframe
from app.ui.manual_metadata_editor import (
    MANUAL_METADATA_DELETE_COLUMN,
    append_manual_metadata_row,
    apply_manual_metadata_editor_changes,
    delete_selected_manual_metadata_rows,
    editor_dataframe_to_manual_records,
    ensure_manual_metadata_rows,
    manual_metadata_rows_to_editor_dataframe,
    reset_manual_metadata_rows,
)
from app.ui.navigation import (
    build_maintainer_links,
    build_navigation_sections,
    build_page_registry,
    build_quick_start_links,
)
from app.ui.page_overview import build_workflow_overview
from app.ui.review_form_helpers import (
    candidate_evidence,
    collect_mapping_review_inputs,
    collect_quality_review_inputs,
    collect_stg_review_inputs,
)
from app.ui import status_blocks
from app.ui.result_overview import artifact_download_key, build_result_artifacts
from app.ui.result_detail_viewer import build_result_detail_sections
from app.ui import session_keys as keys
from app.ui.session_keys import build_session_defaults
from app.ui.value_formatters import format_value
from app.ui.workflow_run_panel import (
    review_replay_control_defaults,
    select_profile_name,
)
from app.ui.workbench_state import WorkbenchState
from app.core.models.ai_ready_score import AiReadyScore
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult
from app.core.models.workflow_profile import WorkflowProfile
from app.core.models.workflow_result import WorkflowResult


class _FakeSessionState(dict):
    def setdefault(self, key, default=None):  # noqa: ANN001
        return super().setdefault(key, default)


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state = _FakeSessionState()
        self.calls: list[tuple[str, object]] = []

    @contextmanager
    def spinner(self, *_args, **_kwargs):
        yield None

    def title(self, value: object) -> None:
        self.calls.append(("title", value))

    def subheader(self, value: object) -> None:
        self.calls.append(("subheader", value))

    def caption(self, value: object) -> None:
        self.calls.append(("caption", value))

    def write(self, value: object) -> None:
        self.calls.append(("write", value))

    def info(self, value: object) -> None:
        self.calls.append(("info", value))

    def columns(self, count):  # noqa: ANN001
        if isinstance(count, int):
            return [_FakeColumn(self, index) for index in range(count)]
        return [_FakeColumn(self, index) for index, _ in enumerate(count)]


class _FakeColumn:
    def __init__(self, parent: _FakeStreamlit, index: int) -> None:
        self.parent = parent
        self.index = index

    def metric(self, label: object, value: object, help=None) -> None:  # noqa: ANN001
        self.parent.calls.append(
            ("metric", {"index": self.index, "label": label, "value": value, "help": help})
        )


def test_session_defaults_use_fresh_mutable_values() -> None:
    first = build_session_defaults()
    second = build_session_defaults()

    first[keys.LATEST_REPORT_PATHS]["json"] = "first.json"
    first[keys.REPORT_EXPORT_HISTORY].append({"json": "first.json"})

    assert second[keys.LATEST_REPORT_PATHS] == {}
    assert second[keys.REPORT_EXPORT_HISTORY] == []


def test_workbench_state_initializes_and_updates_state() -> None:
    fake_state = _FakeSessionState()
    state = WorkbenchState(fake_state)
    state.initialize_defaults()
    state.set_selected_workflow_profile("profile-a")
    state.set_latest_control_plane_preview("preview")
    state.set_latest_execution_package_export_results([{"output_path": "a.json"}])

    assert fake_state[keys.SELECTED_WORKFLOW_PROFILE] == "profile-a"
    assert state.get_latest_control_plane_preview() == "preview"
    assert state.get_latest_execution_package_export_results() == [
        {"output_path": "a.json"}
    ]


def test_workbench_state_reads_uploaded_file_metadata() -> None:
    fake_state = _FakeSessionState(
        {
            keys.UPLOADED_FILE_NAME: "sample.csv",
            keys.UPLOADED_FILE_SIZE: 128,
            keys.UPLOADED_FILE_EXTENSION: "csv",
        }
    )
    state = WorkbenchState(fake_state)

    assert state.get_uploaded_file_name() == "sample.csv"
    assert state.get_uploaded_file_size() == 128
    assert state.get_uploaded_file_extension() == "csv"


def test_result_detail_sections_include_available_result_groups() -> None:
    result = WorkflowResult(
        issues=[
            Issue(
                issue_id="issue-1",
                object_type="field",
                object_name="cust_no",
                issue_type="missing_description",
                severity="medium",
            )
        ],
        mapping_results=[
            MappingResult(
                table_name="customer",
                field_name="cust_no",
                recommended_standard_code="STD_CUSTOMER_NO",
            )
        ],
        ai_ready_scores=[
            AiReadyScore(
                object_name="customer",
                overall_score=82,
                ai_ready_level="B_basic_ready",
            )
        ],
    )

    sections = build_result_detail_sections(result)
    titles = {section.title for section in sections}
    groups = {section.group for section in sections}

    assert "问题清单" in titles
    assert "标准映射推荐" in titles
    assert "AI-ready 评分" in titles
    assert "诊断与语义" in groups
    assert "标准映射与 STG" in groups
    assert "AI 准备度" in groups


def test_manual_metadata_editor_state_actions() -> None:
    state = _FakeSessionState()
    rows = ensure_manual_metadata_rows(state)
    original_count = len(rows)

    append_manual_metadata_row(state)
    assert len(state["manual_metadata_rows"]) == original_count + 1

    dataframe = manual_metadata_rows_to_editor_dataframe(state["manual_metadata_rows"])
    dataframe.loc[0, "field_name"] = "changed_field"
    dataframe.loc[1, MANUAL_METADATA_DELETE_COLUMN] = True
    apply_manual_metadata_editor_changes(state, dataframe)

    assert state["manual_metadata_rows"][0]["field_name"] == "changed_field"

    delete_dataframe = manual_metadata_rows_to_editor_dataframe(
        state["manual_metadata_rows"]
    )
    delete_dataframe.loc[0, MANUAL_METADATA_DELETE_COLUMN] = True
    deleted_count = delete_selected_manual_metadata_rows(state, delete_dataframe)

    assert deleted_count == 1
    assert len(state["manual_metadata_rows"]) == original_count

    records = editor_dataframe_to_manual_records(
        manual_metadata_rows_to_editor_dataframe(state["manual_metadata_rows"])
    )
    assert MANUAL_METADATA_DELETE_COLUMN not in records[0]

    reset_manual_metadata_rows(state)
    assert state["manual_metadata_rows"][0]["field_name"] == "contract_no"


def test_workflow_run_panel_profile_helpers() -> None:
    profile_names = ["metadata_diagnosis_only", "diagnosis_mapping_stg_quality"]

    assert (
        select_profile_name(profile_names, "diagnosis_mapping_stg_quality")
        == "diagnosis_mapping_stg_quality"
    )
    assert select_profile_name(profile_names, "missing") == "metadata_diagnosis_only"
    assert select_profile_name(["custom"], None) == "custom"

    replay_profile = WorkflowProfile(
        name="diagnosis_mapping_stg_quality",
        description="full",
        supports_review_replay=True,
    )
    no_replay_profile = WorkflowProfile(
        name="metadata_diagnosis_only",
        description="diagnosis",
        supports_review_replay=False,
    )
    forced_replay_profile = WorkflowProfile(
        name="diagnosis_mapping_stg_quality_with_review",
        description="with review",
        supports_review_replay=True,
    )

    assert review_replay_control_defaults(replay_profile) == (True, False)
    assert review_replay_control_defaults(no_replay_profile) == (False, True)
    assert review_replay_control_defaults(forced_replay_profile) == (True, True)


def test_page_utils_records_report_history_with_limit(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()

    for index in range(12):
        page_utils.record_report_paths({"json": f"report_{index}.json"})

    assert fake_st.session_state[keys.LATEST_REPORT_PATHS] == {
        "json": "report_11.json"
    }
    assert len(fake_st.session_state[keys.REPORT_EXPORT_HISTORY]) == 10
    assert fake_st.session_state[keys.REPORT_EXPORT_HISTORY][0] == {
        "json": "report_2.json"
    }


def test_page_utils_raw_session_accessors(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    page_utils.set_session_value("page_local_key", {"value": 1})

    assert page_utils.get_session_value("page_local_key") == {"value": 1}
    assert page_utils.get_session_value("missing", "fallback") == "fallback"


def test_page_utils_uploaded_file_state_resets_workflow(monkeypatch, tmp_path: Path) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    fake_st.session_state[keys.WORKFLOW_RESULT] = object()
    fake_st.session_state[keys.LATEST_REPORT_PATHS] = {"json": "old.json"}

    file_path = tmp_path / "sample.csv"
    file_path.write_text("table_name,field_name\ncustomer,customer_id\n", encoding="utf-8")
    page_utils.set_uploaded_file_state(
        file_path=file_path,
        file_signature="abc123",
        source_label="sample",
    )

    assert fake_st.session_state[keys.UPLOADED_FILE_PATH] == str(file_path)
    assert fake_st.session_state[keys.UPLOADED_FILE_NAME] == "sample.csv"
    assert fake_st.session_state[keys.UPLOADED_FILE_SIGNATURE] == "abc123"
    assert fake_st.session_state[keys.WORKFLOW_RESULT] is None
    assert fake_st.session_state[keys.LATEST_REPORT_PATHS] == {}
    assert fake_st.session_state[keys.RESTORED_SESSION_SOURCE] == "sample"


def test_page_utils_task_response_state_records_exports(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    result = {"status": "success"}
    response = SimpleNamespace(
        result=result,
        exported_files={"json": "result.json"},
    )

    page_utils.set_task_response_state(response, file_path="input.csv")

    assert fake_st.session_state[keys.WORKFLOW_RESULT] == result
    assert fake_st.session_state[keys.WORKFLOW_RESULT_FILE_PATH] == "input.csv"
    assert fake_st.session_state[keys.GOVERNANCE_TASK_RESPONSE] is response
    assert fake_st.session_state[keys.LATEST_REPORT_PATHS] == {"json": "result.json"}


def test_page_utils_current_input_prefers_workflow_file(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    fake_st.session_state[keys.UPLOADED_FILE_PATH] = "uploaded.csv"
    fake_st.session_state[keys.WORKFLOW_RESULT_FILE_PATH] = "workflow.csv"

    assert page_utils.get_current_input_file_path() == "workflow.csv"
    assert (
        page_utils.get_current_input_file_path(prefer_workflow_result=False)
        == "uploaded.csv"
    )


def test_page_utils_report_accessors_return_defensive_copies(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    fake_st.session_state[keys.LATEST_REPORT_PATHS] = {"json": "result.json"}
    fake_st.session_state[keys.REPORT_EXPORT_HISTORY] = [{"json": "result.json"}]

    latest = page_utils.get_latest_report_paths()
    history = page_utils.get_report_export_history()
    latest["json"] = "changed.json"
    history[0]["json"] = "changed.json"

    assert fake_st.session_state[keys.LATEST_REPORT_PATHS] == {"json": "result.json"}
    assert fake_st.session_state[keys.REPORT_EXPORT_HISTORY] == [
        {"json": "result.json"}
    ]


def test_page_utils_uploaded_file_accessors(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    fake_st.session_state[keys.UPLOADED_FILE_NAME] = "sample.csv"
    fake_st.session_state[keys.UPLOADED_FILE_SIZE] = 128
    fake_st.session_state[keys.UPLOADED_FILE_EXTENSION] = "csv"

    assert page_utils.get_uploaded_file_name() == "sample.csv"
    assert page_utils.get_uploaded_file_size() == 128
    assert page_utils.get_uploaded_file_extension() == "csv"


def test_page_utils_batch_file_accessors(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    page_utils.set_batch_file_paths(["a.csv", "b.csv"])

    assert page_utils.get_batch_file_paths() == ["a.csv", "b.csv"]


def test_page_overview_forwards_workflow_overview_options() -> None:
    result = SimpleNamespace(
        message="default summary",
        status="success",
        input_table_count=1,
        issue_count=2,
        task_count=3,
        mapping_results=[],
        stg_field_suggestions=[],
        quality_rule_suggestions=[],
        confirmed_mapping_results=[],
        confirmed_stg_suggestions=[],
        confirmed_quality_rules=[],
    )

    overview = build_workflow_overview(
        result,
        title="Custom title",
        summary="Custom summary",
        next_step="Custom next step",
    )

    assert overview.title == "Custom title"
    assert overview.summary == "Custom summary"
    assert overview.next_step == "Custom next step"


def test_page_utils_confirmation_import_accessors(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    page_utils.set_confirmation_import_file_path("input.xlsx")
    page_utils.set_confirmation_validation_result({"ok": True})
    page_utils.set_confirmation_template_diagnosis({"match": "demo"})

    assert page_utils.get_confirmation_import_file_path() == "input.xlsx"
    assert page_utils.get_confirmation_validation_result() == {"ok": True}
    assert page_utils.get_confirmation_template_diagnosis() == {"match": "demo"}


def test_review_form_helpers_collect_mapping_and_stg_inputs() -> None:
    mapping = SimpleNamespace(table_name="customer", field_name="cust_id")
    stg = SimpleNamespace(source_table_name="customer", source_field_name="cust_id")
    values = {
        "mapping_action_customer.cust_id": "accept",
        "mapping_final_customer.cust_id": "CUST_ID",
        "mapping_note_customer.cust_id": "ok",
        "stg_action_customer.cust_id": "edit",
        "stg_final_name_customer.cust_id": "cust_id",
        "stg_final_type_customer.cust_id": "string",
        "stg_note_customer.cust_id": "rename",
    }

    mapping_inputs = collect_mapping_review_inputs([mapping], values.get)
    stg_inputs = collect_stg_review_inputs([stg], values.get)

    assert mapping_inputs["customer.cust_id"] == {
        "review_action": "accept",
        "final_standard_code": "CUST_ID",
        "reviewer_note": "ok",
    }
    assert stg_inputs["customer.cust_id"] == {
        "review_action": "edit",
        "final_stg_field_name": "cust_id",
        "final_data_type": "string",
        "reviewer_note": "rename",
    }


def test_review_form_helpers_collect_quality_inputs_and_evidence() -> None:
    rule = SimpleNamespace(rule_id="rule-1")
    values = {
        "quality_action_rule-1": "accept",
        "quality_expression_rule-1": "amount > 0",
        "quality_severity_rule-1": "high",
        "quality_note_rule-1": "trusted",
    }

    quality_inputs = collect_quality_review_inputs(
        [rule],
        lambda item: item.rule_id,
        values.get,
    )

    assert quality_inputs["rule-1"] == {
        "review_action": "accept",
        "final_rule_expression": "amount > 0",
        "final_severity": "high",
        "reviewer_note": "trusted",
    }
    assert candidate_evidence(
        [
            {
                "standard_code": "CUST_ID",
                "standard_name": "Customer ID",
                "match_score": 0.91,
                "match_reason": "name match",
            }
        ]
    ) == ["CUST_ID | Customer ID | 分数=0.91 | name match"]


def test_page_utils_control_plane_accessors(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    page_utils.set_latest_control_plane_preview("draft")
    page_utils.set_latest_control_plane_result({"status": "draft"})

    assert page_utils.get_latest_control_plane_preview() == "draft"
    assert page_utils.get_latest_control_plane_result() == {"status": "draft"}


def test_page_utils_execution_package_accessors(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    page_utils.set_latest_execution_ready_package({"package_id": "pkg-1"})
    page_utils.set_latest_execution_package_export_results([{"output_path": "a.json"}])

    assert page_utils.get_latest_execution_ready_package() == {"package_id": "pkg-1"}
    assert page_utils.get_latest_execution_package_export_results() == [
        {"output_path": "a.json"}
    ]


def test_execution_package_export_results_are_defensive_copies(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(page_utils, "st", fake_st)
    page_utils.initialize_session_state()
    fake_st.session_state[keys.LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS] = [
        {"output_path": "a.json"}
    ]

    exported = page_utils.get_latest_execution_package_export_results()
    exported[0]["output_path"] = "changed.json"

    assert fake_st.session_state[keys.LATEST_EXECUTION_PACKAGE_EXPORT_RESULTS] == [
        {"output_path": "a.json"}
    ]


def test_value_formatter_handles_common_values() -> None:
    assert format_value(None) == ""
    assert format_value(True) == "是"
    assert format_value(False) == "否"
    assert format_value(3.0) == "3"
    assert format_value(3.14159) == "3.14"
    assert format_value(["a", "", None, "b"]) == "a, b"
    assert format_value({"status": "HIGH", "enabled": True, "empty": None}) == "状态=高; enabled=是"
    assert format_value("success") == "成功"
    assert format_value("True") == "是"


def test_column_labels_localize_dataframe_columns_and_values() -> None:
    dataframe = performance_helpers.pd.DataFrame(
        [
            {
                "table_name": "customer",
                "status": "success",
                "requires_manual_review": True,
                "confidence": 0.91,
            }
        ]
    )

    localized = localize_dataframe(dataframe)

    assert localized.to_dict("records") == [
        {
            "表英文名": "customer",
            "状态": "成功",
            "需要人工复核": "是",
            "置信度": 0.91,
        }
    ]


def test_column_labels_localize_empty_dataframe_columns() -> None:
    dataframe = performance_helpers.pd.DataFrame(columns=["table_name", "status"])

    localized = localize_dataframe(dataframe)

    assert list(localized.columns) == ["表英文名", "状态"]
    assert localized.empty is True


def test_navigation_registry_builds_chinese_sections_and_home_links(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_page(target, **kwargs):  # noqa: ANN001
        page = {"target": target, **kwargs}
        calls.append(page)
        return page

    monkeypatch.setattr("app.ui.navigation.st.Page", fake_page)

    def home_page() -> None:
        return None

    page_by_key = build_page_registry(home_page)
    sections = build_navigation_sections(page_by_key)
    quick_start_links = build_quick_start_links(page_by_key)
    maintainer_links = build_maintainer_links(page_by_key)

    assert page_by_key["home"]["target"] is home_page
    assert page_by_key["home"]["default"] is True
    assert page_by_key["upload"]["title"] == "01 上传元数据"
    assert list(sections) == [
        "开始",
        "核心流程",
        "智能入口",
        "治理管理",
        "交付与批处理",
        "模板与接入",
    ]
    assert [label for _, label, _ in quick_start_links] == [
        "1. 上传文件",
        "2. 开始诊断",
        "3. 进入评审",
        "4. 导出报告",
    ]
    assert [label for _, label, _ in maintainer_links] == [
        "意图运行器",
        "Agent 控制台",
        "配置控制面",
        "质量规则",
    ]
    assert len(calls) == len(page_by_key)


def test_status_block_renders_key_values(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(status_blocks, "st", fake_st)

    status_blocks.render_key_value_block(
        "Overview",
        summary="Ready",
        rows=[("Enabled", True), ("Empty", None)],
    )

    assert fake_st.calls == [
        ("subheader", "Overview"),
        ("caption", "Ready"),
        ("write", "- **Enabled**: `是`"),
    ]


def test_status_block_supports_titleless_empty_state(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(status_blocks, "st", fake_st)

    status_blocks.render_key_value_block(
        None,
        rows=[],
        empty_message="Nothing here.",
    )

    assert fake_st.calls == [("info", "Nothing here.")]


def test_status_block_renders_bullet_list(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(status_blocks, "st", fake_st)

    status_blocks.render_bullet_list("Items", ["alpha", None, "beta"])

    assert fake_st.calls == [
        ("subheader", "Items"),
        ("write", "- alpha"),
        ("write", "- beta"),
    ]


def test_status_block_renders_page_header(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(status_blocks, "st", fake_st)

    status_blocks.render_page_header(
        "Page",
        "Intro",
        caption="Caption",
        info="Info",
    )

    assert fake_st.calls == [
        ("title", "Page"),
        ("write", "Intro"),
        ("caption", "Caption"),
        ("info", "Info"),
    ]


def test_status_block_renders_metric_row(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(status_blocks, "st", fake_st)

    status_blocks.render_metric_row(
        [
            ("Count", 3),
            ("Ready", True, "ready help"),
        ],
    )

    assert fake_st.calls == [
        ("metric", {"index": 0, "label": "Count", "value": "3", "help": None}),
        ("metric", {"index": 1, "label": "Ready", "value": "是", "help": "ready help"}),
    ]


def test_result_overview_artifact_download_key_is_stable() -> None:
    assert (
        artifact_download_key("json", Path("exports") / "result.json")
        == "download_json_exports/result.json"
    )


def test_result_overview_builds_artifacts_with_mime_types() -> None:
    artifacts = build_result_artifacts(
        {"json": "result.json", "markdown": "result.md"},
        mime_by_label={"json": "application/json"},
    )

    assert [artifact.label for artifact in artifacts] == ["json", "markdown"]
    assert [artifact.path for artifact in artifacts] == ["result.json", "result.md"]
    assert [artifact.mime for artifact in artifacts] == ["application/json", None]
    assert build_result_artifacts(None) == []


def test_control_plane_fingerprint_is_stable_and_sha256_like() -> None:
    first = content_fingerprint("profiles:\n  - name: demo\n")
    second = content_fingerprint("profiles:\n  - name: demo\n")
    changed = content_fingerprint("profiles:\n  - name: changed\n")

    assert first == second
    assert first != changed
    assert first.startswith("25::")


def test_control_plane_diff_and_publish_guards() -> None:
    original = "a\nb\n"
    edited = "a\nb\nc\n"

    assert diff_stats(original, edited) == (1, 0)
    assert can_publish_without_save(original, original) is True
    assert can_publish_without_save(original, edited) is False
    assert should_warn_baseline_changed(None, "new") is False
    assert should_warn_baseline_changed("old", "new") is True


def test_large_file_runtime_ready_uses_cached_session_state(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(performance_helpers, "st", fake_st)
    monkeypatch.setattr(
        performance_helpers,
        "get_session_value",
        lambda key, default=None: fake_st.session_state.get(key, default),
    )
    monkeypatch.setattr(
        performance_helpers,
        "set_session_value",
        lambda key, value: fake_st.session_state.__setitem__(key, value),
    )
    monkeypatch.setattr(
        performance_helpers,
        "load_metadata_file_cached",
        lambda file_path, signature: {"loaded": (file_path, signature)},
    )
    monkeypatch.setattr(performance_helpers, "semantic_index_enabled", lambda: False)
    monkeypatch.setattr(performance_helpers, "warm_semantic_mapping_index", lambda: True)
    monkeypatch.setattr(
        performance_helpers,
        "association_rule_learning_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        performance_helpers,
        "load_quality_rule_associations",
        lambda: None,
    )

    first = performance_helpers.ensure_large_file_runtime_ready("input.csv", "sig-1")
    second = performance_helpers.ensure_large_file_runtime_ready("input.csv", "sig-1")

    assert first == {
        "metadata_parser_ready": True,
        "semantic_index_ready": True,
        "quality_rule_learning_ready": True,
    }
    assert second == first
    assert fake_st.session_state[performance_helpers.LARGE_FILE_RUNTIME_WARMUP_KEY] == "sig-1"


def test_records_to_dataframe_accepts_model_dict_and_object() -> None:
    class ModelRecord:
        def model_dump(self) -> dict[str, object]:
            return {"kind": "model", "value": 1}

    dataframe = performance_helpers.records_to_dataframe(
        [
            ModelRecord(),
            {"kind": "dict", "value": 2},
            SimpleNamespace(kind="object", value=3),
        ]
    )

    assert dataframe.to_dict("records") == [
        {"kind": "model", "value": 1},
        {"kind": "dict", "value": 2},
        {"kind": "object", "value": 3},
    ]


def test_json_ready_payload_normalizes_nested_values() -> None:
    class ModelRecord:
        def model_dump(self) -> dict[str, object]:
            return {
                "path": Path("outputs") / "result.json",
                "items": {1, 2},
                "child": SimpleNamespace(value="nested"),
            }

    payload = performance_helpers.json_ready_payload(ModelRecord())

    assert payload == {
        "path": "outputs\\result.json",
        "items": [1, 2],
        "child": {"value": "nested"},
    }


def test_dataframe_filter_helpers_cover_options_and_selection() -> None:
    dataframe = performance_helpers.pd.DataFrame(
        [
            {"status": "open", "owner_role": "admin"},
            {"status": "closed", "owner_role": "owner"},
            {"status": "open", "owner_role": "owner"},
        ]
    )

    assert performance_helpers.dataframe_filter_options(dataframe, "status") == [
        "closed",
        "open",
    ]
    assert performance_helpers.dataframe_filter_options(dataframe, "missing") == []

    filtered = performance_helpers.filter_dataframe_by_values(
        dataframe,
        "status",
        ["open"],
    )
    assert filtered.to_dict("records") == [
        {"status": "open", "owner_role": "admin"},
        {"status": "open", "owner_role": "owner"},
    ]


def test_content_signature_is_stable_md5() -> None:
    from app.ui.workbench_cache import content_signature

    assert content_signature(b"abc") == "900150983cd24fb0d6963f7d28e17f72"
