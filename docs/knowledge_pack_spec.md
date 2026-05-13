# Governance Knowledge Pack Specification

本文档定义当前项目第一版治理知识包（knowledge packs）的组成、字段说明和维护方式。

## 1. 知识包目标

当前知识包用于增强两类能力：

1. 命名治理增强
   - 缩写展开
   - token 规范化
   - 更可解释的命名建议

2. 标准映射建议
   - 将字段元数据映射到企业标准字段库
   - 输出候选分数、匹配原因和低置信度提示

当前版本完全基于本地规则和字典驱动，不依赖 LLM、embedding 或外部服务。

## 2. 知识包类型

### 2.1 abbreviation_dict.csv

路径：

- `app/data/dictionaries/abbreviation_dict.csv`

作用：

- 为字段名、表名中的缩写提供展开规则
- 供命名检查与标准映射共同使用

字段定义：

| 列名 | 含义 | 是否必填 | 示例 |
| --- | --- | --- | --- |
| `abbreviation` | 缩写 token | 是 | `cust` |
| `expanded_form` | 展开后的标准词 | 是 | `customer` |
| `category` | 缩写类别 | 否 | `business_entity` |
| `notes` | 备注 | 否 | `Common customer abbreviation` |

### 2.2 root_word_dict.csv

路径：

- `app/data/dictionaries/root_word_dict.csv`

作用：

- 为命名治理提供 token 标准词根
- 用于 token 规范化和“是否在治理词典中”的基础判断

字段定义：

| 列名 | 含义 | 是否必填 | 示例 |
| --- | --- | --- | --- |
| `token` | 原始 token | 是 | `temporary` |
| `normalized_form` | 规范化后的词 | 是 | `temporary` |
| `category` | 词类别 | 否 | `lifecycle` |
| `notes` | 备注 | 否 | `Canonical temporary token` |

### 2.3 standard_fields.csv

路径：

- `app/data/standards/standard_fields.csv`

作用：

- 提供标准字段库
- 供 `standard_mapping_recommendation` skill 进行候选推荐

字段定义：

| 列名 | 含义 | 是否必填 | 示例 |
| --- | --- | --- | --- |
| `standard_code` | 标准字段编码 | 是 | `customer_id` |
| `standard_name` | 标准字段英文名 | 是 | `customer_id` |
| `standard_name_cn` | 标准字段中文名 | 否 | `客户ID` |
| `description` | 标准字段说明 | 否 | `Unique identifier for a customer.` |
| `data_type` | 建议数据类型 | 否 | `string` |
| `business_domain` | 业务域 | 否 | `customer` |
| `aliases` | 同义名或别名，建议分号分隔 | 否 | `cust_id;customer_identifier` |

## 3. 当前维护方式

当前版本建议采用以下维护方式：

1. 由治理或建模同事直接维护 CSV 文件
2. 每次新增缩写、词根、标准字段时保持列结构不变
3. `aliases` 字段统一用分号分隔多个值
4. 新增条目时尽量保证词义明确，避免一词多义

## 4. 使用建议

1. 缩写词典应优先收录企业内部高频缩写
2. 词根词典应覆盖核心业务实体、指标词、生命周期词
3. 标准字段库质量会直接影响映射推荐效果
4. 如果推荐效果不理想，应优先补知识包，而不是先增加复杂算法

## 5. 后续扩展方向

- TODO: 后续可增加领域专属词典和中文别名词典
- TODO: 后续可加入标准字段层级、主题域、主数据/交易数据分类
- TODO: 后续可在语义版中叠加 embedding 检索与 LLM 解释，但当前版本不引入
