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

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.page_overview import build_config_edit_overview, build_validation_overview
from app.ui.result_overview import render_result_overview

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
            st.dataframe(dataframe, use_container_width=True)
        return
    st.json(content)


def _render_diff_preview(original_text: str, edited_text: str, asset_name: str) -> None:
    diff_lines = list(
        unified_diff(
            original_text.splitlines(),
            edited_text.splitlines(),
            fromfile=f"{asset_name} (current)",
            tofile=f"{asset_name} (edited)",
            lineterm="",
        )
    )
    if diff_lines:
        st.code("\n".join(diff_lines), language="diff")
    else:
        st.info("当前编辑内容与原始内容一致。")


st.title("治理控制面")
st.write("集中管理本地治理配置资产，支持预览、校验、保存、发布和回滚。")

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

    st.caption(
        f"类型: {asset['asset_type']} | 文件: {asset['file_path']} | 可编辑: {asset['editable']}"
    )

    metric_status, metric_validated, metric_published = st.columns(3)
    metric_status.metric("状态", status.get("current_status") or "unknown")
    metric_validated.metric("最近校验", status.get("last_validated_at") or "N/A")
    metric_published.metric("最近发布", status.get("last_published_at") or "N/A")
    if status.get("last_error_message"):
        st.error(status["last_error_message"])
    if status.get("current_status") == "published":
        st.warning("当前资产已发布，继续编辑前会先记录一次新备份。")

    content_left, content_right = st.columns(2)
    with content_left:
        with st.expander("当前内容预览", expanded=True):
            _render_preview(asset_format, content)

    with content_right:
        editor_value = _serialize_content(asset_format, content)
        edited_text = st.text_area(
            "编辑内容",
            value=editor_value,
            height=420,
            key=f"control_plane_editor_{selected_asset_name}",
        )
        st.session_state["latest_control_plane_preview"] = edited_text

    st.subheader("变更预览")
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
            st.session_state["latest_control_plane_result"] = validation_result
            if validation_result.is_valid:
                st.success("当前编辑内容校验通过。")
            else:
                st.error("当前编辑内容校验未通过。")

    backup_result = None
    if action_col2.button("保存", type="primary", use_container_width=True):
        latest_preview = st.session_state.get("latest_control_plane_preview")
        if latest_preview is None:
            st.warning("没有可保存的编辑内容。")
        else:
            try:
                save_result = service.save_asset(selected_asset_name, latest_preview)
            except Exception as exc:
                st.error(f"保存资产失败: {exc}")
            else:
                st.session_state["latest_control_plane_result"] = save_result
                if save_result.status in {"draft", "published"}:
                    st.success(save_result.message)
                else:
                    st.error(save_result.message)
                st.rerun()

    if action_col3.button("发布", use_container_width=True):
        try:
            publish_result = service.publish_asset(selected_asset_name)
        except Exception as exc:
            st.error(f"发布资产失败: {exc}")
        else:
            st.session_state["latest_control_plane_result"] = publish_result
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
                st.session_state["latest_control_plane_result"] = backup_result
                if backup_result.status in {"draft", "published"}:
                    st.success(backup_result.message)
                else:
                    st.error(backup_result.message)
                st.rerun()

    latest_result = st.session_state.get("latest_control_plane_result")
    if latest_result is not None:
        if hasattr(latest_result, "validation_result") and latest_result.validation_result is not None:
            render_result_overview(build_config_edit_overview(latest_result))
            render_result_overview(build_validation_overview(latest_result.validation_result))
        elif hasattr(latest_result, "is_valid"):
            render_result_overview(build_validation_overview(latest_result))
        else:
            st.subheader("最近结果")
            if hasattr(latest_result, "model_dump"):
                st.json(latest_result.model_dump())
            else:
                st.write(latest_result)

    st.subheader("最近备份")
    if not backups:
        st.info("当前资产还没有备份。")
    else:
        for backup_path in backups[:10]:
            st.write(f"- `{backup_path}`")
