"""Quality rule review and export workbench."""

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

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
    load_quality_rule_overrides,
    save_quality_rule_review_records,
)
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.skills.quality_rule_recommendation import QualityRuleRecommendationSkill
from app.core.utils.result_utils import (
    confirmed_quality_rules_to_dataframe,
    cross_field_quality_rules_to_dataframe,
    quality_review_queue_summary_to_dataframe,
    quality_rule_review_summary_to_dataframe,
    quality_rules_to_dataframe,
    rule_export_results_to_dataframe,
)

initialize_session_state()

st.title("Quality Rules")
st.write(
    "Review field-level and cross-field quality rules, replay saved overrides, "
    "and export confirmed rule assets."
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
    all_records = load_quality_rule_overrides()
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
    st.session_state["workflow_result"] = result
    return save_result, replay_summary


result: WorkflowResult | None = st.session_state.get("workflow_result")
uploaded_file_path = st.session_state.get("workflow_result_file_path") or st.session_state.get(
    "uploaded_file_path"
)

if result is None:
    st.warning("No workflow result is available yet. Run a quality rule workflow first.")
else:
    field_suggestions = list(result.quality_rule_suggestions)
    cross_field_rules = list(result.cross_field_quality_rules)
    review_queue = _reviewable_suggestions(result)
    confirmed_rules = result.confirmed_quality_rules
    stored_overrides = load_quality_rule_overrides()
    override_lookup = build_quality_rule_override_lookup(stored_overrides)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Field Rules", len(field_suggestions))
    metric_col2.metric("Cross-Field Rules", len(cross_field_rules))
    metric_col3.metric("Confirmed Rules", len(confirmed_rules))
    metric_col4.metric(
        "Low Confidence",
        summarize_review_queue(review_queue).get("low_confidence_rule_count", 0),
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

    st.subheader("Field-Level Quality Rules")
    if visible_field_suggestions:
        st.dataframe(
            quality_rules_to_dataframe(visible_field_suggestions),
            use_container_width=True,
        )
    else:
        st.info("No field-level quality rules match the current filters.")

    st.subheader("Cross-Field Quality Rules")
    if visible_cross_field_rules:
        st.dataframe(
            cross_field_quality_rules_to_dataframe(visible_cross_field_rules),
            use_container_width=True,
        )
    else:
        st.info("No cross-field quality rules match the current filters.")

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
                    st.write(
                        f"Suggested expression: `{rule.rule_expression or 'N/A'}` | "
                        f"severity=`{rule.severity}` | priority=`{rule.priority or 'N/A'}` | "
                        f"confidence=`{rule.confidence if rule.confidence is not None else 'N/A'}` | "
                        f"review_priority=`{rule.review_priority or 'N/A'}`"
                    )
                    if rule.field_group:
                        st.caption(f"Field group: {', '.join(rule.field_group)}")
                    st.caption(rule.reason or "No recommendation reason available.")
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
            review_inputs = {}
            for rule in visible_review_queue:
                key = _rule_key(rule)
                review_inputs[key] = {
                    "review_action": st.session_state.get(f"quality_action_{key}"),
                    "final_rule_expression": st.session_state.get(
                        f"quality_expression_{key}"
                    ),
                    "final_severity": st.session_state.get(f"quality_severity_{key}"),
                    "reviewer_note": st.session_state.get(f"quality_note_{key}"),
                }

            records = build_quality_rule_review_records_from_results(
                visible_review_queue,
                review_inputs,
                source="streamlit_quality_rules",
            )
            try:
                save_result, _ = _persist_review_records(records, result, review_queue)
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
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True)
    else:
        st.info("No quality rule review summary is available.")

    st.subheader("Quality Review Queue Summary")
    queue_summary = result.quality_review_queue_summary or summarize_review_queue(review_queue)
    queue_df = quality_review_queue_summary_to_dataframe(queue_summary)
    if not queue_df.empty:
        st.dataframe(queue_df, use_container_width=True)
    else:
        st.info("No quality review queue summary is available.")

    st.subheader("Confirmed Quality Rules")
    if confirmed_rules:
        st.dataframe(
            confirmed_quality_rules_to_dataframe(confirmed_rules),
            use_container_width=True,
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
            st.session_state["workflow_result"] = result
            st.session_state["latest_execution_ready_package"] = package
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
                    st.session_state["workflow_result"] = rerun_result
                    st.session_state["workflow_result_file_path"] = uploaded_file_path
                    st.success("Quality workflow re-ran with saved overrides applied.")

    with col2:
        export_format = st.selectbox(
            "Export format",
            options=["custom JSON", "dbt YAML"],
            key="quality_rule_export_format",
        )
        if st.button("Export Confirmed Rules"):
            current_result: WorkflowResult = st.session_state["workflow_result"]
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
                    st.session_state["workflow_result"] = current_result
                    st.success("Confirmed quality rules were exported.")
                except Exception as exc:
                    st.error(f"Failed to export confirmed quality rules: {exc}")

    st.subheader("Rule Export Results")
    export_df = rule_export_results_to_dataframe(result.rule_export_results)
    if not export_df.empty:
        st.dataframe(export_df, use_container_width=True)
    else:
        st.info("No rule export results are available.")

    with st.expander("Stored Quality Rule Overrides", expanded=False):
        if stored_overrides:
            st.dataframe(
                pd.DataFrame([record.model_dump() for record in stored_overrides]),
                use_container_width=True,
            )
        else:
            st.info("No stored quality rule overrides found.")
