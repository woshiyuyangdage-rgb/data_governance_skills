"""Lightweight governance control plane page."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_overview import build_config_edit_overview, build_validation_overview
from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_latest_control_plane_result,
    initialize_session_state,
    set_latest_control_plane_result,
)
from app.ui.performance_helpers import (
    render_json_section,
    render_lazy_dataframe_section,
)
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import (
    render_bullet_list,
    render_metric_row,
    render_page_header,
)

ensure_project_root_on_path()

from app.core.control_plane.control_plane_service import ControlPlaneService

initialize_session_state()

service = ControlPlaneService()


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


render_page_header(
    "治理控制面",
    "集中管理本地治理配置资产，支持状态查看、只读预览、校验、发布和回滚。",
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

    st.caption(
        f"类型: {asset['asset_type']} | 文件: {asset['file_path']} | 格式: {asset_format}"
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

    st.subheader("当前配置")
    st.info("此页面只用于查看和维护配置状态，不提供在线编辑。配置内容调整请通过代码仓库变更后再发布。")
    with st.expander("查看当前内容", expanded=False):
        _render_preview(asset_format, content)

    st.subheader("维护操作")
    action_col1, action_col2, action_col3 = st.columns(3)
    if action_col1.button("校验当前配置", type="primary", use_container_width=True):
        try:
            validation_result = service.validate_asset(selected_asset_name)
        except Exception as exc:
            st.error(f"配置校验失败: {exc}")
        else:
            set_latest_control_plane_result(validation_result)
            if validation_result.is_valid:
                st.success("当前配置校验通过。")
            else:
                st.error("当前配置校验未通过。")

    if action_col2.button("发布当前配置", use_container_width=True):
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
    backup_choice = action_col3.selectbox(
        "回滚入口",
        options=[""] + backup_options,
        format_func=lambda value: "请选择备份" if value == "" else Path(value).name,
        key=f"backup_choice_{selected_asset_name}",
    )
    if action_col3.button("从备份回滚", use_container_width=True):
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
