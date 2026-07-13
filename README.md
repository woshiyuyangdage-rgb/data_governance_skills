# Data Governance Skills

`data_governance_skills` 是一个本地单用户的数据治理技能 MVP。它以规则和配置为核心，把 Excel/CSV 元数据转换为可诊断、可评审、可交付的治理资产，并把知识文档、切片、检索日志和问答评测转化为可治理的 RAG 质量问题清单。当前能力覆盖元数据质量诊断、标准映射、STG 结构建议、质量规则推荐、人工确认回放、执行包生成、治理就绪度评估、AI-ready 评分、RAG 知识库质量检测、Text-to-SQL 元数据准备度评估、整改待办、组合视图和本地交付物导出。

项目当前定位是“治理决策支持与交付资产生成工具”，不是线上执行平台。它不直接连接生产数据库执行质量检查，不调用云端 LLM，不创建外部工单，也不集成企业流程系统。

## 一句话说明

这个项目把分散在元数据表、治理规则、人工评审记录和交付文档里的工作，收敛成一套本地可运行、可测试、可导出的规则化数据治理流程。

## 新手入口

### 解决什么问题

数据治理工作通常从 Excel/CSV 元数据开始，但后续会很快变成一串分散动作：检查字段是否完整、判断命名是否规范、对齐标准字段、设计 STG、补质量规则、找业务确认、整理整改清单、导出交付材料。手工做这些事容易重复、口径不稳、过程不可追踪。

本项目把这些动作产品化为本地流程：

- 统一读取和规范化元数据文件。
- 自动诊断表和字段层面的元数据质量问题。
- 推荐标准字段映射、STG 结构和质量规则。
- 保存人工评审结果，并在后续流程中回放。
- 生成确认质量规则、执行准备包、治理工作包和交付包。
- 评估治理就绪度和 AI-ready 水平，生成整改动作、待办、SLA 状态、进度快照和组合汇总。

### 适合的场景

- 快速评估一批表的元数据质量。
- 将源字段映射到本地标准字段体系。
- 为贴源层或 STG 层生成结构建议。
- 根据字段、映射、STG 和领域规则生成质量规则草案。
- 判断表资产是否适合进入 RAG、Text-to-SQL 和智能数据助手。
- 检测制度文档、数据标准文档、元数据说明和知识切片是否适合进入 RAG。
- 评估表、字段、主外键、指标、枚举、权限和样例 SQL 是否足够支撑 Text-to-SQL。
- 固化人工确认结果，避免重复评审。
- 输出治理报告、确认工作簿、执行包和整改待办。

### 不适合的场景

- 直接连接生产数据库执行质量检查。
- 替代 dbt、Great Expectations、Soda 等执行引擎。
- 多用户审批、权限管理、流程流转或工单创建。
- 调用云端 LLM 或外部企业系统。

### 环境要求

项目代码使用 Python 3.10+ 语法，建议使用 Python 3.13 作为本地开发和测试解释器。不要使用 Python 3.9 运行测试或应用。

```bash
python --version
python -m pip install -r requirements.txt
```

如果你的系统默认 `python` 不是 3.10+，请显式使用满足版本要求的解释器运行命令。

### 快速开始

启动 FastAPI：

```bash
python -m uvicorn app.main:app --reload
```

启动 Streamlit 工作台：

```bash
python -m streamlit run app/ui/streamlit_app.py
```

运行基础检查：

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check app tests
python -m app.maintenance doctor
python -m pytest -q
```

仓库包含 GitHub Actions 配置，推送到 `main`、提交 pull request 或手动触发时，会在 Python 3.10 和 3.13 上运行同一套检查。

### 输入文件

支持 `.csv` 和 `.xlsx`。

推荐输入字段：

| 字段 | 说明 |
| --- | --- |
| `table_name` | 必填，表名 |
| `field_name` | 推荐填写，用于字段级治理 |
| `table_name_cn`、`table_description`、`schema_name`、`system_name` | 可选，补充表级上下文 |
| `field_name_cn`、`field_description`、`data_type`、`nullable` | 可选，补充字段级上下文 |

参考文件：

- `docs/input_template_spec.md`
- `app/data/samples/sample_metadata.csv`

文件型接口请求示例：

```json
{
  "file_path": "app/data/samples/sample_metadata.csv"
}
```

本地文件读取和输出目录默认限制在项目安全根目录内。可信单用户场景如果需要读取或写入项目目录外的本地路径，可以通过 `DATA_GOVERNANCE_ALLOWED_LOCAL_ROOTS` 追加允许根目录；多个目录使用当前操作系统的路径分隔符连接。

### 常规治理流程

```text
上传元数据 -> 解析与规范化 -> 质量诊断 -> 标准映射 -> STG 结构建议 -> 质量规则推荐 -> 人工评审 -> 评审结果回放 -> 确认规则 -> 执行准备包 -> 治理就绪度 -> AI-ready 评分 -> 整改计划 -> 待办 -> 组合评估 -> 报告和交付资产
```

### 主要入口

- Streamlit 工作台：`app/ui/streamlit_app.py`
- FastAPI 应用：`app/main.py`
- 任务接口：`app/api/routes_jobs.py`
- 报告接口：`app/api/routes_reports.py`
- 技能接口：`app/api/routes_skills.py`
- 维护命令：`app/maintenance.py`

常用 FastAPI 端点：

- `GET /health`
- `GET /jobs/`
- `GET /skills/`
- `POST /jobs/run-governance-task`
- `POST /jobs/interpret-governance-task`
- `POST /jobs/agent-shell/plan`
- `POST /jobs/call-tool`
- `GET /jobs/capability-manifest`
- `GET /jobs/config-assets`
- `POST /jobs/review-quality-rules`
- `POST /jobs/build-execution-ready-package`
- `POST /jobs/assess-governance-readiness`
- `POST /jobs/build-governance-backlog`
- `POST /jobs/assess-governance-portfolio`
- `POST /jobs/assess-rag-quality`
- `POST /jobs/assess-text-to-sql-readiness`
- `GET /jobs/project-workspaces`
- `POST /jobs/project-workspaces`

## 六个产品级 Skills

| Skill | 目的 | 主要输出 |
| --- | --- | --- |
| `metadata-diagnosis-skill` | 将原始表字段元数据转换成完整性、技术对象、命名质量、诊断和任务输出 | `completeness_output`、`technical_output`、`naming_output`、`diagnosis_output`、`task_output` |
| `data-standard-mapping-skill` | 推荐源字段到标准字段的映射，并支持评审结果回放 | `mapping_results`、`confirmed_mapping_results`、`unmapped_fields`、`mapping_summary` |
| `stg-standardization-skill` | 基于元数据、映射、命名信号和转换规则推荐 STG 表字段结构 | `stg_suggestions`、`stg_field_suggestions`、`confirmed_stg_suggestions`、`stg_summary` |
| `data-quality-rule-skill` | 推荐字段级、领域感知和跨字段质量规则，并支持确认 | `quality_rule_suggestions`、`cross_field_quality_rules`、`confirmed_quality_rules`、`quality_rule_summary` |
| `dbt-governance-skill` | 将确认规则打包为执行准备资产和 dbt 兼容 YAML | `execution_ready_package`、`execution_package_export_results`、`dbt_yaml` |
| `governance-report-skill` | 导出报告、确认工作簿、交付包、AI-ready 评分、待办、组合视图和进度快照 | `exported_files`、`readiness_scores`、`ai_ready_scores`、`governance_backlog_items`、`progress_snapshot`、`governance_delivery_manifest` |

技能清单由 `app/config/skill_registry.yaml` 配置，读取入口在 `app/core/skills/skill_catalog.py`。

## 维护者入口

### 架构分层

```text
app/
  api/        FastAPI 路由、请求模型和工具响应封装
  config/     YAML 配置资产
  core/       解析、规则、技能、编排、治理逻辑、适配器、报告和模型
  data/       示例输入、词典、标准字段、本地覆盖记录和本地状态
  ui/         Streamlit 本地工作台
docs/         规格说明和设计文档
outputs/      本地运行导出的报告和交付资产
tests/        pytest 自动化测试
```

### 核心模块

| 模块 | 位置 | 功能 |
| --- | --- | --- |
| API 接口层 | `app/api/` | 暴露 FastAPI 路由、请求模型、任务接口、报告接口和工具响应封装。`routes_jobs.py` 是聚合入口，具体任务路由按领域拆分。 |
| UI 工作台 | `app/ui/` | Streamlit 多页面工作台，覆盖上传、诊断、报告、评审、Agent Shell、工具控制台、配置面板、质量规则、执行包、就绪度、AI-ready 评分、待办、组合视图、项目工作区、平台数据总览和交付包。 |
| 编排引擎 | `app/core/orchestrator/` | 将解析、技能、评审、执行包、就绪度、AI-ready 评分、待办和组合评估串成 workflow profile。 |
| 元数据解析 | `app/core/parser/` | 读取 CSV、Excel 和批量输入，转换为内部表字段模型，并处理解析异常。 |
| 输入适配 | `app/core/intake/` | 诊断企业元数据模板、匹配列别名、选择最佳 sheet，并规范化输入文件。 |
| 领域与模板 | `app/core/domain/`、`app/core/templates/` | 加载领域治理包和项目模板，根据文本或表结构匹配领域提示，并应用模板默认值。 |
| 治理技能 | `app/core/skills/` | 按产品级 skill 拆分元数据诊断、标准映射、STG 标准化、质量规则、dbt 治理和治理报告能力。 |
| 规则与词典 | `app/core/rules/`、`app/core/normalize/`、`app/data/` | 管理命名规则、技术关键词、标准字段、缩写词典、根词词典和文本清洗拆词逻辑。 |
| 评审与回放 | `app/core/review/` | 保存映射、STG 和质量规则评审记录，管理人工覆盖结果，并在后续流程中回放确认意见。 |
| 质量与执行包 | `app/core/adapters/`、`app/core/tools/` | 生成确认质量规则、执行准备包、规则导出结果和工具化调用响应。 |
| 治理度量 | `app/core/governance/` | 评估治理就绪度和表级 AI-ready 水平，分类治理缺口，生成整改动作、工作包、待办、SLA 状态、进度快照和组合汇总。AI-ready 评分覆盖可发现性、可理解性、语义一致性、标准化程度、质量可控性、安全可控性、可追溯性和 AI 应用适配性。 |
| Text-to-SQL 准备度 | `app/core/governance/text_to_sql_readiness_assessor.py` | 基于本地规则评估表识别、字段理解、关系推断、指标口径、枚举解释、安全权限和样例查询支撑情况，输出准备度分数、等级、短板、风险和建议。 |
| 知识治理 | `app/core/knowledge/` | 加载本地治理知识包，并基于规则检测 RAG 文档、切片、检索结果、回答评测和权限标签中的质量风险。 |
| 交付包 | `app/core/delivery/` | 导出确认工作簿，导入确认结果，构建治理交付 manifest 和本地交付包。 |
| 意图、上下文与 Agent Shell | `app/core/intent/`、`app/core/context/`、`app/core/agent/` | 将自然语言意图解析为治理任务，解析运行上下文，生成执行计划并保存本地会话。当前为规则 + 本地传统 NLP 能力，不调用云端 LLM。 |
| 工具注册与适配 | `app/core/tools/`、`app/core/adapters/` | 暴露本地工具注册表、工具调用、OpenAI/MCP/native schema 导出和适配器调用封装。 |
| 配置控制面 | `app/core/control_plane/`、`app/config/` | 管理 YAML 配置资产、校验、保存、发布和本地状态记录。 |
| 审计与报告 | `app/core/audit/`、`app/core/reports/` | 记录工具执行 trace，导出 JSON、Markdown、Excel 报告。 |
| 数据模型 | `app/core/models/` | 定义表字段、诊断问题、映射、STG、质量规则、工作流结果、待办、就绪度、AI-ready 评分和交付包等 Pydantic 模型。 |
| 维护工具 | `app/maintenance.py` | 提供 doctor、quick-check、命令清单、本地缓存清理等维护入口。 |

### 代码边界

- 新代码应优先引用产品级 skill 包，例如 `app.core.skills.data_quality_rule_skill`。
- `app.core.skills.quality_rule_recommendation` 等旧扁平路径仅作为兼容 wrapper 保留。
- 配置资产集中放在 `app/config/`。
- 本地运行产物应放在 `outputs/` 或被 `.gitignore` 忽略的 `app/data/` 子目录中。

### Workflow Profiles

常用 profile：

- `metadata_diagnosis_only`：只做元数据诊断。
- `mapping_only`：只做标准映射。
- `diagnosis_plus_mapping`：诊断 + 标准映射。
- `diagnosis_mapping_stg`：诊断 + 映射 + STG 建议。
- `diagnosis_mapping_stg_with_review`：映射和 STG 后引入人工评审。
- `diagnosis_mapping_stg_quality`：进一步推荐质量规则。
- `diagnosis_mapping_stg_quality_with_review`：质量规则推荐后支持评审。
- `diagnosis_mapping_stg_quality_package_with_review`：生成确认规则和执行准备包。
- `governance_readiness_assessment`：评估治理就绪度和 AI-ready 水平。
- `full_governance_work_package`：构建治理工作包。
- `governance_backlog_build`：构建治理整改待办。
- `full_governance_backlog_package`：生成完整待办包。
- `governance_portfolio_assessment`：做治理组合评估。
- `full_governance_portfolio_package`：生成组合评估交付包。
- `stg_only_from_mapping`：基于映射结果只做 STG 建议。
- `quality_only_from_stg`：基于 STG 结果只做质量规则推荐。
- `quality_only_from_stg_with_review`：质量规则推荐并纳入评审。

### 本地维护命令

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m app.maintenance doctor
python -m app.maintenance quick-check
python -m app.maintenance commands
python -m app.maintenance clean-local-artifacts
python -m ruff check app tests
```

### 文档索引

核心规格：

- `docs/input_template_spec.md`
- `docs/knowledge_pack_spec.md`
- `docs/workflow_profile_spec.md`
- `docs/intent_interpreter_spec.md`
- `docs/context_resolver_spec.md`
- `docs/agent_shell_spec.md`
- `docs/tool_contract_spec.md`
- `docs/control_plane_spec.md`
- `docs/adapter_layer_spec.md`

治理能力规格：

- `docs/stg_structure_spec.md`
- `docs/quality_rule_recommendation_spec.md`
- `docs/domain_aware_quality_spec.md`
- `docs/quality_rule_review_and_export_spec.md`
- `docs/execution_ready_package_spec.md`
- `docs/governance_readiness_and_remediation_spec.md`
- `docs/governance_backlog_tracking_spec.md`
- `docs/governance_portfolio_and_progress_spec.md`
- `docs/governance_delivery_package_spec.md`
- `docs/batch_processing_and_incremental_rerun_spec.md`
- `docs/workbook_import_and_roundtrip_spec.md`
- `docs/domain_governance_packs_and_project_templates_spec.md`
- `docs/enterprise_metadata_intake_adapters_spec.md`
- `docs/enterprise_delivery_adapters_spec.md`
- `docs/project_workspace_spec.md`
- `docs/platform_metrics_spec.md`

维护文档：

- `docs/maintenance_commands.md`

### 当前边界

项目当前不提供：

- 云端 LLM 推理和外部在线模型服务。
- 数据库质量检查的真实执行。
- 外部向量数据库、在线检索服务或 RAG 编排平台。
- Text-to-SQL 模型推理、SQL 自动生成、SQL 执行或查询结果校验。
- 调度器、队列、Docker 或 CI 编排。
- dbt、Great Expectations、Soda 或自定义 SQL 引擎的运行时执行。
- 多用户审批、权限体系或数据库持久化状态。
- Jira、飞书、钉钉、TAPD、邮件、SharePoint、BI 等外部系统集成。
- 自动负责人分派、提醒发送或工单创建。

当前导出的资产主要是本地 JSON、Markdown、Excel 和 YAML 文件，用于评审、交付、归档，以及未来接入企业适配器。
