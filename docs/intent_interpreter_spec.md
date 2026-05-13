# Intent Interpreter Specification

## 1. Why an Intent Interpreter

The current project already has stable workflow profiles and a unified governance task router.

That means the execution side is standardized, but the user still needs to manually choose a profile or construct a structured request.

The intent interpreter adds a lightweight transition layer:

- input: short natural-language task text
- output: a standard `GovernanceTaskRequest`

It is not a chat agent. It is a controlled and explainable task-to-profile mapper.

## 2. Input and Output

Input:

- a short natural-language task string
- optional `file_path`

Output:

- `InterpretedIntent`
- `GovernanceTaskRequest`
- optionally `GovernanceTaskResponse` after execution

## 3. Matching Strategy

The current version uses:

- rule-based keyword matching
- configurable keyword lists from YAML
- simple text cleaning and substring matching

The interpreter does not use:

- LLMs
- embeddings
- semantic retrieval
- open-ended planning

## 4. Supported Intent Types

### `quick_scan`

- target profile: `metadata_diagnosis_only`
- examples:
  - help me run a quick diagnosis
  - metadata diagnosis only
  - 元数据诊断

### `standard_recommendation`

- default target profile: `diagnosis_plus_mapping`
- examples:
  - run standard mapping
  - recommend standard fields
  - 标准映射

### `structure_suggestion`

- default target profile: `diagnosis_mapping_stg`
- examples:
  - generate stg structure suggestions
  - run stg suggestion
  - stg结构建议

### `quality_rule_recommendation`

- default target profile: `diagnosis_mapping_stg_quality`
- examples:
  - recommend data quality rules
  - generate quality rule recommendations
  - 推荐质量规则

### `replay_confirmed`

- target profile: `diagnosis_mapping_stg_with_review`
- examples:
  - rerun with overrides
  - confirmed replay
  - 按已确认结果重跑

### `mapping_only_request`

- target profile: `mapping_only`

### `stg_only_request`

- target profile: `stg_only_from_mapping`

### `quality_only_request`

- target profile: `quality_only_from_stg`

## 5. Supported Parameter Recognition

The current interpreter can infer:

- `export_reports`
- `apply_review_replay`
- `confirmed_mode`

These are inferred by keyword matching and then mapped into a standard task request where applicable.

## 6. Ambiguous or Missing Intent

If no workflow intent is matched strongly enough:

- the interpreter falls back to `metadata_diagnosis_only`
- `fallback_used=True`
- the message explicitly states that a safe default was applied

This is preferred over aggressive guessing.

## 7. Current Boundary

The current interpreter is intentionally limited:

- single-turn only
- keyword-based only
- no multi-round parameter completion
- no conversation memory
- no autonomous agent planning

## 8. Future Extension Notes

- TODO: add optional LLM-based intent parsing behind a safe fallback path
- TODO: add multi-turn parameter completion for missing file path or export choices
- TODO: connect interpreted intents to future planner or tool-calling layers
