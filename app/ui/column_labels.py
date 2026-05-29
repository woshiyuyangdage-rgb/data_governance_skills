"""Chinese display labels for dataframe columns in the Streamlit UI."""

from __future__ import annotations

import pandas as pd

from app.ui.value_formatters import format_value


COLUMN_LABELS: dict[str, str] = {
    "accepted_count": "已接受数",
    "acceptance_criteria": "验收标准",
    "action": "治理动作",
    "action_suggestion": "处理建议",
    "ai_consumption_risk_score": "AI 消费风险分",
    "ai_ready_level": "AI-ready 等级",
    "ai_risk": "AI 风险",
    "ai_usage_risks_joined": "AI 使用风险",
    "applicable_scenarios_joined": "适用场景",
    "backlog_id": "待办 ID",
    "best_candidate_code": "最佳候选标准编码",
    "best_candidate_score": "最佳候选分数",
    "blocked_by": "阻塞原因",
    "business_domain": "业务域",
    "business_impact_score": "业务影响分",
    "business_object": "业务对象",
    "business_purpose": "业务用途",
    "candidate_count": "候选数",
    "category": "分类",
    "compatibility": "兼容性",
    "completion_criteria": "完成标准",
    "confidence": "置信度",
    "confirmation_source": "确认来源",
    "confirmed_source": "确认来源",
    "context_evidence_joined": "上下文证据",
    "core_fields_joined": "核心字段",
    "created_at": "创建时间",
    "dependency_notes": "依赖说明",
    "dimension": "维度",
    "edited_count": "已编辑数",
    "engine_hints": "执行引擎提示",
    "evidence_joined": "证据",
    "expected_benefit": "预期收益",
    "expected_output": "预期产出",
    "export_format": "导出格式",
    "export_formats_joined": "可导出格式",
    "field_group": "字段分组",
    "field_name": "字段英文名",
    "field_name_cn": "字段中文名",
    "field_rule_count": "字段规则数",
    "gap_count": "缺口数",
    "gap_type": "缺口类型",
    "generated_at": "生成时间",
    "generated_description": "生成描述",
    "generated_summary": "生成摘要",
    "governance_action": "治理建议",
    "governance_risk_score": "治理风险分",
    "impact_scope": "影响范围",
    "issue_flags_joined": "问题标记",
    "issue_id": "问题 ID",
    "issue_ids_joined": "关联问题 ID",
    "issue_type": "问题类型",
    "key_concepts_joined": "关键概念",
    "manual_review_count": "人工复核数",
    "mapping_source": "映射来源",
    "mapping_status": "映射状态",
    "match_basis": "匹配依据",
    "match_reason": "匹配原因",
    "match_score": "匹配分数",
    "message": "消息",
    "notes": "备注",
    "object_name": "对象名称",
    "object_type": "对象类型",
    "optimized_description": "优化后描述",
    "optimized_summary": "优化后摘要",
    "original_description": "原描述",
    "output_path": "输出路径",
    "owner_role": "责任角色",
    "package_id": "包 ID",
    "package_name": "包名称",
    "priority": "优先级",
    "priority_reason": "优先级原因",
    "priority_score": "优先级分",
    "quality_tags_joined": "质量标签",
    "readiness_level": "就绪等级",
    "readiness_score": "就绪度分数",
    "readiness_score_count": "就绪度评分数",
    "reason": "原因",
    "recommendation_source": "推荐来源",
    "recommended_actions_joined": "推荐动作",
    "recommended_data_type": "推荐数据类型",
    "recommended_field_name": "推荐字段名",
    "recommended_priority": "推荐优先级",
    "recommended_stg_field_name": "推荐 STG 字段名",
    "recommended_stg_field_name_cn": "推荐 STG 字段中文名",
    "recommended_stg_table_name": "推荐 STG 表名",
    "recommended_stg_table_name_cn": "推荐 STG 表中文名",
    "recommended_standard_code": "推荐标准编码",
    "recommended_standard_name": "推荐标准名称",
    "recommended_standard_name_cn": "推荐标准中文名",
    "rejected_count": "已拒绝数",
    "remediation_action_count": "整改动作数",
    "remediation_complexity_score": "整改复杂度分",
    "requires_manual_review": "需要人工复核",
    "review_action": "评审动作",
    "review_priority": "评审优先级",
    "reviewer_note": "评审备注",
    "risk": "风险",
    "risk_flags_joined": "风险标记",
    "risk_hint": "风险提示",
    "risk_level": "风险等级",
    "risks_joined": "风险",
    "rule_count": "规则数",
    "rule_description": "规则说明",
    "rule_expression": "规则表达式",
    "rule_id": "规则 ID",
    "rule_name": "规则名称",
    "rule_scope": "规则范围",
    "rule_type": "规则类型",
    "semantic_type": "语义类型",
    "severity": "严重程度",
    "severity_score": "严重程度分",
    "skill_name": "技能名称",
    "source_data_type": "源数据类型",
    "source_field_name": "源字段名",
    "source_field_name_cn": "源字段中文名",
    "source_profile": "来源方案",
    "source_signals": "来源信号",
    "source_table_name": "源表名",
    "standard_code": "标准编码",
    "standard_name": "标准名称",
    "status": "状态",
    "suggested_cycle": "建议周期",
    "suggested_owner_role": "建议责任角色",
    "suggestion": "建议",
    "summary": "摘要",
    "table_name": "表英文名",
    "table_name_cn": "表中文名",
    "target_field_name": "目标字段名",
    "target_table_name": "目标表名",
    "task_id": "任务 ID",
    "total_reviewed_count": "总评审数",
    "updated_at": "更新时间",
    "urgency_score": "紧急度分",
}


VALUE_LOCALIZED_COLUMNS = {
    "action",
    "ai_ready_level",
    "category",
    "confirmation_source",
    "confirmed_source",
    "export_format",
    "mapping_source",
    "mapping_status",
    "match_basis",
    "object_type",
    "owner_role",
    "priority",
    "readiness_level",
    "recommendation_source",
    "review_action",
    "risk_level",
    "rule_scope",
    "rule_type",
    "severity",
    "status",
    "suggested_owner_role",
}


def _localize_dataframe_values(dataframe: pd.DataFrame) -> pd.DataFrame:
    display_dataframe = dataframe.copy()
    for column in display_dataframe.columns:
        if column in VALUE_LOCALIZED_COLUMNS:
            display_dataframe[column] = display_dataframe[column].map(format_value)
        elif (
            pd.api.types.is_bool_dtype(display_dataframe[column])
            or display_dataframe[column].map(lambda value: isinstance(value, bool)).any()
        ):
            display_dataframe[column] = display_dataframe[column].map(
                lambda value: format_value(value) if isinstance(value, bool) else value
            )
    return display_dataframe


def localize_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a dataframe with Chinese display labels and values."""
    if dataframe.empty:
        return dataframe
    display_dataframe = _localize_dataframe_values(dataframe)
    renamed_columns = {
        column: COLUMN_LABELS.get(str(column), str(column))
        for column in display_dataframe.columns
    }
    return display_dataframe.rename(columns=renamed_columns)


def localize_dataframe_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a dataframe with Chinese display column labels."""
    return localize_dataframe(dataframe)
