# Metadata Input Template Specification

本文档定义本地 MVP 第一版支持的元数据导入模板，适用于 `.csv` 与 `.xlsx` 文件。

## 1. 支持的输入粒度

当前支持两种输入粒度：

1. `table-level only`
   - 仅提供表级信息。
   - 最少需要 `table_name` 列。
   - 适合先做表级诊断或快速试跑。

2. `table + field-level`
   - 同时提供表级和字段级信息。
   - 这是第一版主推模板。
   - 推荐所有字段按“每行一个字段”的方式提供。

建议优先使用 `table + field-level` 模板，因为当前 P0 pipeline 在字段命名、字段中文名、字段描述等方面可以给出更完整的诊断结果。

## 2. 标准输入列

第一版标准输入列如下：

| 列名 | 含义 | 是否必填 | 示例值 |
| --- | --- | --- | --- |
| `table_name` | 英文技术表名 | 是 | `customer_master` |
| `table_name_cn` | 中文表名 | 否 | `客户主数据` |
| `table_description` | 表级业务描述 | 否 | `Active customer master data.` |
| `schema_name` | 所属 schema | 否 | `dim` |
| `system_name` | 来源系统或域 | 否 | `crm` |
| `field_name` | 英文字段名 | `table + field-level` 模板中建议必填；若该行仅表示表级信息可为空 | `customer_id` |
| `field_name_cn` | 中文字段名 | 否 | `客户ID` |
| `field_description` | 字段业务描述 | 否 | `Unique customer identifier.` |
| `data_type` | 字段数据类型 | 否 | `string` |
| `nullable` | 是否可空，支持 `true/false`、`yes/no`、`1/0`、`y/n` | 否 | `false` |

## 3. 行组织方式

### 3.1 主推方式：table + field-level

- 每一行代表一个字段。
- 同一张表的表级信息在多行中重复出现。
- parser 会按 `table_name` 聚合为一张表，并把多个字段行聚合为一个表对象。

示例：

| table_name | table_name_cn | field_name | field_name_cn |
| --- | --- | --- | --- |
| `customer_master` | `客户主数据` | `customer_id` | `客户ID` |
| `customer_master` | `客户主数据` | `customer_name` | `客户名称` |

### 3.2 table-level only

- 若当前只有表级信息，可以只提供表级列。
- 最少需要 `table_name`。
- 如果沿用标准模板，也可以保留 `field_name` 等列，但该行字段值留空。

示例：

| table_name | table_name_cn | table_description | field_name |
| --- | --- | --- | --- |
| `user_audit_log` | `用户审计日志` | `Internal audit log table.` |  |

## 4. 必填规则

- 所有模板都必须包含 `table_name` 列。
- 若文件包含字段级信息，则应包含 `field_name` 列。
- `field_name` 的单元格允许为空，用于表达“仅有表级信息”的行。
- 除 `table_name`、`field_name` 外，其余列均允许为空。

## 5. 文件格式要求

- 支持 `.csv`
- 支持 `.xlsx`
- 第一行必须是列名
- 建议使用 UTF-8 编码的 CSV
- 建议不要在单元格中放复杂公式或合并单元格

## 6. 解析约定

当前 parser 的处理约定如下：

- 去除字符串首尾空格
- 空字符串统一按空值处理
- `nullable` 会标准化为布尔值或空值
- 同一张表下，如果某一行 `field_name` 为空，但 `table_name` 有值，仍会保留该表对象
- 当前版本不做复杂字段推断，也不自动补全缺失元数据

## 7. 推荐做法

- 内部同事提交模板时，优先基于 `app/data/samples/sample_metadata.csv` 复制填写
- 若先只拿到表级清单，也可以先用 `table-level only` 跑通闭环
- 若希望获得更完整的诊断和治理任务，建议尽量补充字段级元数据
