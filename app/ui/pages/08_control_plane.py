"""Lightweight governance control plane page."""

from difflib import unified_diff
import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_latest_control_plane_preview,
    get_latest_control_plane_result,
    get_session_value,
    initialize_session_state,
    set_latest_control_plane_preview,
    set_latest_control_plane_result,
    set_session_value,
)
from app.ui.control_plane_helpers import (
    can_publish_without_save,
    content_fingerprint,
    diff_stats,
    should_warn_baseline_changed,
)
from app.ui.page_overview import build_config_edit_overview, build_validation_overview
from app.ui.performance_helpers import render_json_section, render_lazy_dataframe_section
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import render_bullet_list, render_metric_row, render_page_header

ensure_project_root_on_path()

from app.core.control_plane.control_plane_service import ControlPlaneService

initialize_session_state()

service = ControlPlaneService()


def _serialize_content(asset_format: str, content: object) -> str:
    if asset_format == "yaml":
        return yaml.safe_dump(content or {}, allow_unicode=True, sort_keys=False)
    if asset_format == "json":
        return json.dumps(content or {}, ensure_ascii=False, indent=2)
    if asset_format == "csv":
        dataframe = pd.DataFrame(content or [])
        return dataframe.to_csv(index=False)
    return str(content)


def _render_preview(asset_format: str, content: object) -> None:
    if asset_format == "csv":
        dataframe = pd.DataFrame(content or [])
        if dataframe.empty:
            st.info("CSV 资产当前为空。")
        else:
            render_lazy_dataframe_section(
                "当前内容预览",
                dataframe,
                compact=True,
                key_prefix="control_plane_csv_preview",
            )
        return
    render_json_section("当前内容预览", content, compact=True)


def _render_diff_preview(original_text: str, edited_text: str, asset_name: str) -> None:
    diff_lines = list(
        unified_diff(
            original_text.splitlines(),
            edited_text.splitlines(),
            fromfile=f"{asset_name} (当前)",
            tofile=f"{asset_name} (已编辑)",
            lineterm="",
        )
    )
    if diff_lines:
        st.code("\n".join(diff_lines), language="diff")
    else:
        st.info("当前编辑内容与原始内容一致。")


render_page_header(
    "治理控制面",
    "集中管理本地治理配置资产，支持预览、校验、保存、发布和回滚。",
)

asset_rows = service.list_assets_with_status()
asset_lookup = {row["asset_name"]: row for row in asset_rows}
asset_names = list(asset_lookup.keys())

if not asset_names:
    st.warning("当前没有注册可管理的配置资产。")
else:
    selected_asset_name = st.selectbox("管理资产", options=asset_names)
    asset_payload = service.get_asset_content(selected_asset_name)
    asset = asset_payload["asset"]
    status = asset_payload["status"]
    asset_format = str(asset_payload["format"])
    content = asset_payload["content"]
    editor_value = _serialize_content(asset_format, content)
    baseline_key = f"control_plane_baseline_{selected_asset_name}"
    current_baseline = content_fingerprint(editor_value)
    previous_baseline = get_session_value(baseline_key)
    if should_warn_baseline_changed(previous_baseline, current_baseline):
        st.warning("该资产的磁盘内容已经变化，请确认当前编辑区是否仍然基于最新内容。")
    set_session_value(baseline_key, current_baseline)

    st.caption(
        f"类型: {asset['asset_type']} | 文件: {asset['file_path']} | 可编辑: {asset['editable']}"
    )

    render_metric_row(
        [
            ("状态", status.get("current_status") or "未知"),
            ("最近校验", status.get("last_validated_at") or "N/A"),
            ("最近发布", status.get("last_published_at") or "N/A"),
        ],
    )
    if status.get("last_error_message"):
        st.error(status["last_error_message"])
    if status.get("current_status") == "published":
        st.warning("当前资产已发布，继续编辑前会先记录一次新备份。")

    content_left, content_right = st.columns(2)
    with content_left:
        with st.expander("当前内容预览", expanded=True):
            _render_preview(asset_format, content)

    with content_right:
        edited_text = st.text_area(
            "编辑内容",
            value=editor_value,
            height=420,
            key=f"control_plane_editor_{selected_asset_name}",
        )
        set_latest_control_plane_preview(edited_text)

    st.subheader("变更预览")
    added_lines, removed_lines = diff_stats(editor_value, edited_text)
    render_metric_row(
        [
            ("新增行", added_lines),
            ("删除行", removed_lines),
            ("是否有变更", "是" if added_lines or removed_lines else "否"),
        ],
    )
    _render_diff_preview(editor_value, edited_text, selected_asset_name)

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    if action_col1.button("校验", use_container_width=True):
        try:
            validation_result = service.validate_asset_preview(
                selected_asset_name,
                edited_text,
            )
        except Exception as exc:
            st.error(f"预览校验失败: {exc}")
        else:
            set_latest_control_plane_result(validation_result)
            if validation_result.is_valid:
                st.success("当前编辑内容校验通过。")
            else:
                st.error("当前编辑内容校验未通过。")

    backup_result = None
    if action_col2.button("保存", type="primary", use_container_width=True):
        latest_preview = get_latest_control_plane_preview()
        if latest_preview is None:
            st.warning("没有可保存的编辑内容。")
        elif latest_preview == editor_value:
            st.info("编辑内容没有变化，无需保存。")
        else:
            try:
                save_result = service.save_asset(selected_asset_name, latest_preview)
            except Exception as exc:
                st.error(f"保存资产失败: {exc}")
            else:
                set_latest_control_plane_result(save_result)
                if save_result.status in {"draft", "published"}:
                    st.success(save_result.message)
                else:
                    st.error(save_result.message)
                st.rerun()

    if action_col3.button("发布", use_container_width=True):
        if not can_publish_without_save(editor_value, edited_text):
            st.warning("当前有未保存变更，请先保存并通过校验后再发布。")
            st.stop()
        validation_before_publish = service.validate_asset_preview(
            selected_asset_name,
            edited_text,
        )
        if not validation_before_publish.is_valid:
            set_latest_control_plane_result(validation_before_publish)
            st.error("发布前校验未通过，请先修正配置。")
            st.stop()
        try:
            publish_result = service.publish_asset(selected_asset_name)
        except Exception as exc:
            st.error(f"发布资产失败: {exc}")
        else:
            set_latest_control_plane_result(publish_result)
            if publish_result.status == "published":
                st.success(publish_result.message)
            else:
                st.error(publish_result.message)
            st.rerun()

    backups = service.list_asset_backups(selected_asset_name)
    backup_options = backups[:10]
    backup_choice = action_col4.selectbox(
        "回滚入口",
        options=[""] + backup_options,
        format_func=lambda value: "请选择备份" if value == "" else Path(value).name,
        key=f"backup_choice_{selected_asset_name}",
    )
    if action_col4.button("回滚", use_container_width=True):
        if not backup_choice:
            st.warning("请先选择一个备份。")
        else:
            try:
                backup_result = service.restore_asset_from_backup(
                    selected_asset_name,
                    backup_choice,
                )
            except Exception as exc:
                st.error(f"回滚失败: {exc}")
            else:
                set_latest_control_plane_result(backup_result)
                if backup_result.status in {"draft", "published"}:
                    st.success(backup_result.message)
                else:
                    st.error(backup_result.message)
                st.rerun()

    latest_result = get_latest_control_plane_result()
    if latest_result is not None:
        if hasattr(latest_result, "validation_result") and latest_result.validation_result is not None:
            render_result_overview(build_config_edit_overview(latest_result))
            render_result_overview(build_validation_overview(latest_result.validation_result))
        elif hasattr(latest_result, "is_valid"):
            render_result_overview(build_validation_overview(latest_result))
        else:
            st.subheader("最近结果")
            if hasattr(latest_result, "model_dump"):
                render_json_section("最近结果", latest_result)
            else:
                st.write(latest_result)

    render_bullet_list(
        "最近备份",
        [f"`{backup_path}`" for backup_path in backups[:10]],
        empty_message="当前资产还没有备份。",
    )
