"""Quality rule review and export workbench."""

from datetime import datetime
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_uploaded_file_signature,
    get_workflow_result,
    get_session_value,
    initialize_session_state,
    set_latest_execution_ready_package,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
)
from app.core.review.quality_batch_review_service import (
    bulk_accept_by_rule_type,
    bulk_mark_manual_review_by_low_confidence,
    summarize_review_queue,
)
from app.core.review.quality_override_store import (
    build_quality_rule_key,
    build_quality_rule_override_lookup,
    save_quality_rule_review_records,
)
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.skills.data_quality_rule_skill import QualityRuleRecommendationSkill
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview
from app.ui.review_form_helpers import collect_quality_review_inputs
from app.ui.performance_helpers import (
    records_to_dataframe,
    render_deferred_dataframe_section,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_metric_row, render_page_header
from app.ui.workbench_cache import (
    confirmed_quality_rules_to_dataframe,
    cross_field_quality_rules_to_dataframe,
    clear_review_override_caches,
    load_quality_rule_overrides_cached,
    quality_review_queue_summary_to_dataframe,
    quality_rule_review_summary_to_dataframe,
    quality_rules_to_dataframe,
    rule_export_results_to_dataframe,
)

initialize_session_state()

render_page_header(
    "Quality Rules",
    (
        "Review field-level and cross-field quality rules, replay saved overrides, "
        "and export confirmed rule assets."
    ),
)


def _cross_field_as_suggestions(result: WorkflowResult) -> list[QualityRuleSuggestion]:
    return [
        QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
        for rule in result.cross_field_quality_rules
    ]


def _reviewable_suggestions(result: WorkflowResult) -> list[QualityRuleSuggestion]:
    return list(result.quality_rule_suggestions) + _cross_field_as_suggestions(result)


def _rule_key(rule: QualityRuleSuggestion) -> str:
    return build_quality_rule_key(
        rule.source_table_name,
        rule.source_field_name,
        rule.rule_type,
        rule_scope=rule.rule_scope,
        field_group=rule.field_group,
    )


def _filter_rules(
    rules: list[QualityRuleSuggestion],
    selected_tables: list[str],
    selected_rule_types: list[str],
    selected_priorities: list[str],
    confidence_range: tuple[float, float],
) -> list[QualityRuleSuggestion]:
    min_confidence, max_confidence = confidence_range
    filtered = []
    for rule in rules:
        if selected_tables and rule.source_table_name not in selected_tables:
            continue
        if selected_rule_types and rule.rule_type not in selected_rule_types:
            continue
        priority = rule.review_priority or "unspecified"
        if selected_priorities and priority not in selected_priorities:
            continue
        if rule.confidence is not None and not (
            min_confidence <= float(rule.confidence) <= max_confidence
        ):
            continue
        filtered.append(rule)
    return filtered


def _persist_review_records(
    records: list[QualityRuleReviewRecord],
    result: WorkflowResult,
    review_queue: list[QualityRuleSuggestion],
) -> tuple[dict[str, str | int], dict[str, object]]:
    save_result = save_quality_rule_review_records(records)
    all_records = load_quality_rule_overrides_cached(get_uploaded_file_signature())
    reviewed_suggestions, _, replay_summary = apply_quality_rule_overrides_to_results(
        review_queue,
        all_records,
    )
    confirmed_rules = build_confirmed_quality_rules(review_queue, all_records)
    result.quality_rule_suggestions = [
        rule for rule in reviewed_suggestions if rule.rule_scope != "cross_field"
    ]
    result.confirmed_quality_rules = confirmed_rules
    result.quality_rule_review_summary = summarize_quality_rule_review_records(
        all_records,
        confirmed_count=len(confirmed_rules),
    )
    result.quality_review_queue_summary = summarize_review_queue(reviewed_suggestions)
    set_workflow_result_state(result)
    return save_result, replay_summary


result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()

if result is None:
    st.warning("No workflow result is available yet. Run a quality rule workflow first.")
else:
    render_result_overview(
        build_workflow_overview(
            result,
            title="质量规则总览",
            next_step="先确认规则，再导出或构建执行包。",
        )
    )

    field_suggestions = list(result.quality_rule_suggestions)
    cross_field_rules = list(result.cross_field_quality_rules)
    review_queue = _reviewable_suggestions(result)
    confirmed_rules = result.confirmed_quality_rules
    stored_overrides = load_quality_rule_overrides_cached(get_uploaded_file_signature())
    override_lookup = build_quality_rule_override_lookup(stored_overrides)

    render_metric_row(
        [
            ("Field Rules", len(field_suggestions)),
            ("Cross-Field Rules", len(cross_field_rules)),
            ("Confirmed Rules", len(confirmed_rules)),
            (
                "Low Confidence",
                summarize_review_queue(review_queue).get("low_confidence_rule_count", 0),
            ),
        ],
    )

    st.subheader("Rule Filters")
    all_tables = sorted({rule.source_table_name for rule in review_queue})
    all_rule_types = sorted({rule.rule_type for rule in review_queue})
    all_priorities = sorted({rule.review_priority or "unspecified" for rule in review_queue})
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        selected_tables = st.multiselect("Table", options=all_tables)
    with filter_col2:
        selected_rule_types = st.multiselect("Rule type", options=all_rule_types)
    with filter_col3:
        selected_priorities = st.multiselect("Review priority", options=all_priorities)
    with filter_col4:
        confidence_range = st.slider(
            "Confidence",
            min_value=0.0,
            max_value=1.0,
            value=(0.0, 1.0),
            step=0.05,
        )

    visible_review_queue = _filter_rules(
        review_queue,
        selected_tables,
        selected_rule_types,
        selected_priorities,
        confidence_range,
    )
    visible_field_suggestions = [
        rule for rule in visible_review_queue if rule.rule_scope != "cross_field"
    ]
    visible_cross_field_keys = {
        _rule_key(rule) for rule in visible_review_queue if rule.rule_scope == "cross_field"
    }
    visible_cross_field_rules = [
        rule
        for rule in cross_field_rules
        if _rule_key(QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule))
        in visible_cross_field_keys
    ]

    with st.expander("Field-Level Quality Rules", expanded=True):
        render_deferred_dataframe_section(
            "Field-Level Quality Rules",
            lambda: quality_rules_to_dataframe(visible_field_suggestions),
            empty_message="No field-level quality rules match the current filters.",
            compact=True,
            key_prefix="quality_field_rules",
            auto_render=len(visible_field_suggestions) <= 80,
        )

    with st.expander("Cross-Field Quality Rules", expanded=False):
        render_deferred_dataframe_section(
            "Cross-Field Quality Rules",
            lambda: cross_field_quality_rules_to_dataframe(visible_cross_field_rules),
            empty_message="No cross-field quality rules match the current filters.",
            compact=True,
            key_prefix="quality_cross_field_rules",
        )

    st.subheader("Batch Review")
    batch_col1, batch_col2 = st.columns(2)
    with batch_col1:
        if st.button("Accept High-Confidence not_null"):
            high_confidence_not_null = [
                rule
                for rule in review_queue
                if rule.rule_type == "not_null" and (rule.confidence or 0.0) >= 0.7
            ]
            records = bulk_accept_by_rule_type(
                high_confidence_not_null,
                "not_null",
                source="streamlit_batch_review",
            )
            if not records:
                st.warning("No high-confidence not_null rules were available.")
            else:
                try:
                    save_result, _ = _persist_review_records(records, result, review_queue)
                    clear_review_override_caches()
                    st.success(
                        f"Saved {save_result['saved_count']} batch accept review records."
                    )
                except Exception as exc:
                    st.error(f"Failed to save batch accept records: {exc}")
    with batch_col2:
        low_confidence_threshold = st.number_input(
            "Low-confidence threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.4,
            step=0.05,
        )
        if st.button("Mark Low-Confidence For Manual Review"):
            records = bulk_mark_manual_review_by_low_confidence(
                review_queue,
                threshold=float(low_confidence_threshold),
                source="streamlit_batch_review",
            )
            if not records:
                st.warning("No low-confidence rules were available.")
            else:
                try:
                    save_result, _ = _persist_review_records(records, result, review_queue)
                    clear_review_override_caches()
                    st.success(
                        f"Saved {save_result['saved_count']} manual review records."
                    )
                except Exception as exc:
                    st.error(f"Failed to save low-confidence review records: {exc}")

    review_actions = ["accept", "reject", "edit", "mark_for_manual_review"]
    if visible_review_queue:
        st.subheader("Manual Review")
        with st.form("quality_rule_review_form"):
            for rule in visible_review_queue:
                key = _rule_key(rule)
                existing = override_lookup.get(key)
                label = f"{key}"
                with st.expander(label, expanded=False):
                    render_explanation_block(
                        "推荐说明",
                        summary=rule.reason or "No recommendation reason available.",
                        details=[
                            ("建议表达式", rule.rule_expression or "N/A"),
                            ("严重度", rule.severity),
                            ("优先级", rule.priority or "N/A"),
                            ("置信度", rule.confidence),
                            ("评审优先级", rule.review_priority or "N/A"),
                            ("推荐来源", rule.recommendation_source),
                            ("匹配依据", rule.match_basis or "N/A"),
                            ("字段组", rule.field_group),
                        ],
                        evidence=rule.learning_context,
                        next_step="确认、拒绝或编辑后再保存评审记录。",
                    )
                    if rule.notes:
                        st.caption(rule.notes)
                    if existing is not None:
                        st.info(
                            "Saved override: "
                            f"`{existing.review_action}` | "
                            f"expression=`{existing.final_rule_expression or 'N/A'}` | "
                            f"severity=`{existing.final_severity or 'N/A'}`"
                        )
                    default_action = (
                        existing.review_action
                        if existing is not None and existing.review_action in review_actions
                        else "accept"
                    )
                    st.selectbox(
                        "Review action",
                        review_actions,
                        index=review_actions.index(default_action),
                        key=f"quality_action_{key}",
                    )
                    st.text_input(
                        "Final rule expression",
                        value=(
                            existing.final_rule_expression
                            if existing is not None
                            and existing.final_rule_expression is not None
                            else rule.rule_expression or ""
                        ),
                        key=f"quality_expression_{key}",
                    )
                    st.selectbox(
                        "Final severity",
                        ["high", "medium", "low"],
                        index=["high", "medium", "low"].index(
                            (
                                existing.final_severity
                                if existing is not None
                                and existing.final_severity in {"high", "medium", "low"}
                                else rule.severity
                                if rule.severity in {"high", "medium", "low"}
                                else "medium"
                            )
                        ),
                        key=f"quality_severity_{key}",
                    )
                    st.text_area(
                        "Reviewer note",
                        value=(
                            existing.reviewer_note
                            if existing is not None and existing.reviewer_note is not None
                            else ""
                        ),
                        height=80,
                        key=f"quality_note_{key}",
                    )

            save_clicked = st.form_submit_button("Save Quality Rule Reviews", type="primary")

        if save_clicked:
            review_inputs = collect_quality_review_inputs(
                visible_review_queue,
                _rule_key,
                get_session_value,
            )

            records = build_quality_rule_review_records_from_results(
                visible_review_queue,
                review_inputs,
                source="streamlit_quality_rules",
            )
            try:
                save_result, _ = _persist_review_records(records, result, review_queue)
                clear_review_override_caches()
                st.success(
                    f"Saved {save_result['saved_count']} quality rule review records."
                )
            except Exception as exc:
                st.error(f"Failed to save quality rule reviews: {exc}")
    elif review_queue:
        st.info("No reviewable rules match the current filters.")

    st.subheader("Quality Rule Review Summary")
    summary = result.quality_rule_review_summary or summarize_quality_rule_review_records(
        stored_overrides,
        confirmed_count=len(confirmed_rules),
    )
    summary_df = quality_rule_review_summary_to_dataframe(summary)
    with st.expander("Quality Rule Review Summary", expanded=False):
        render_lazy_dataframe_section(
            "Quality Rule Review Summary",
            summary_df,
            empty_message="No quality rule review summary is available.",
            compact=True,
            key_prefix="quality_review_summary",
        )

    st.subheader("Quality Review Queue Summary")
    queue_summary = result.quality_review_queue_summary or summarize_review_queue(review_queue)
    queue_df = quality_review_queue_summary_to_dataframe(queue_summary)
    with st.expander("Quality Review Queue Summary", expanded=False):
        render_lazy_dataframe_section(
            "Quality Review Queue Summary",
            queue_df,
            empty_message="No quality review queue summary is available.",
            compact=True,
            key_prefix="quality_review_queue",
        )

    st.subheader("Confirmed Quality Rules")
    if confirmed_rules:
        with st.expander("Confirmed Quality Rules", expanded=False):
            render_lazy_dataframe_section(
                "Confirmed Quality Rules",
                confirmed_quality_rules_to_dataframe(confirmed_rules),
                empty_message="No confirmed quality rules are available yet.",
                compact=True,
                key_prefix="confirmed_quality_rules",
            )
        if st.button("Build Execution Package From Confirmed Rules"):
            builder = ExecutionPackageBuilder()
            package = builder.build_package(
                confirmed_rules,
                profile_name="streamlit_quality_rules",
                trace_metadata={"source": "streamlit_quality_rules"},
            )
            result.execution_ready_package = package
            result.execution_package_summary = builder.summarize_package(package)
            set_workflow_result_state(result)
            set_latest_execution_ready_package(package)
            st.success("Execution-ready package was built from confirmed quality rules.")
    else:
        st.info("No confirmed quality rules are available yet.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Re-run With Quality Overrides"):
            if not uploaded_file_path:
                st.warning("No input file path is available. Run a file-based workflow first.")
            else:
                try:
                    with st.spinner("Re-running quality workflow with saved overrides..."):
                        rerun_result = run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
                            uploaded_file_path
                        )
                except Exception as exc:
                    st.error(f"Failed to rerun with quality overrides: {exc}")
                else:
                    set_workflow_result_state(rerun_result, file_path=uploaded_file_path)
                    st.success("Quality workflow re-ran with saved overrides applied.")

    with col2:
        export_format = st.selectbox(
            "Export format",
            options=["custom JSON", "dbt YAML"],
            key="quality_rule_export_format",
        )
        if st.button("Export Confirmed Rules"):
            current_result: WorkflowResult | None = get_workflow_result()
            if current_result is None:
                st.warning("No workflow result is available to export.")
                st.stop()
            current_rules = current_result.confirmed_quality_rules
            if not current_rules:
                st.warning("No confirmed quality rules are available to export.")
            else:
                adapter = RuleExportAdapter()
                output_dir = PROJECT_ROOT / "outputs" / "rule_exports"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                try:
                    if export_format == "custom JSON":
                        export_result = adapter.export_custom_json_rules(
                            current_rules,
                            str(output_dir / f"confirmed_quality_rules_{timestamp}.json"),
                        )
                    else:
                        export_result = adapter.export_dbt_tests_yaml(
                            current_rules,
                            str(output_dir / f"confirmed_quality_rules_{timestamp}_dbt.yml"),
                        )
                    current_result.rule_export_results.append(export_result)
                    set_workflow_result_state(current_result)
                    st.success("Confirmed quality rules were exported.")
                except Exception as exc:
                    st.error(f"Failed to export confirmed quality rules: {exc}")

    st.subheader("Rule Export Results")
    with st.expander("Rule Export Results", expanded=False):
        render_deferred_dataframe_section(
            "Rule Export Results",
            lambda: rule_export_results_to_dataframe(result.rule_export_results),
            empty_message="No rule export results are available.",
            compact=True,
            key_prefix="quality_rule_exports",
        )

    with st.expander("Stored Quality Rule Overrides", expanded=False):
        if stored_overrides:
            render_deferred_dataframe_section(
                "Stored Quality Rule Overrides",
                lambda: records_to_dataframe(stored_overrides),
                compact=True,
                key_prefix="stored_quality_overrides",
            )
        else:
            st.info("No stored quality rule overrides found.")
