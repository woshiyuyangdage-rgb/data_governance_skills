# Workflow Profile Specification

## 1. Why Workflow Profiles

The current project already contains multiple runnable governance workflows:

- metadata diagnosis
- standard mapping recommendation
- STG structure suggestion
- quality rule recommendation
- review replay with local overrides

Without a profile layer, these workflows stay as separate entrypoints. That is workable for engineering, but unstable for future frontends or agent callers.

Workflow profiles solve this by defining a small set of named governance task types with fixed execution stages.

## 2. Profile Definition

Each workflow profile is defined by:

- `name`
- `enabled`
- `description`
- `stages`
- `supports_review_replay`
- `default_report_mode`

The current version uses explicit profile selection only. It does not attempt natural-language intent understanding.

## 3. Supported Profiles

### `metadata_diagnosis_only`

- Stages: `diagnosis`
- Input: metadata file
- Output: P0 diagnosis issues and governance tasks
- Use case: quick problem scan

### `diagnosis_plus_mapping`

- Stages: `diagnosis`, `mapping`
- Input: metadata file
- Output: diagnosis plus standard field recommendations
- Use case: standard field suggestion

### `diagnosis_mapping_stg`

- Stages: `diagnosis`, `mapping`, `stg`
- Input: metadata file
- Output: diagnosis, mapping, and STG structure suggestions
- Use case: structure standardization suggestion

### `diagnosis_mapping_stg_with_review`

- Stages: `diagnosis`, `mapping`, `stg`, `review_replay`
- Input: metadata file
- Output: diagnosis, mapping, STG, and confirmed results after local override replay
- Use case: rerun with historical human confirmation

### `diagnosis_mapping_stg_quality`

- Stages: `diagnosis`, `mapping`, `stg`, `quality_rule_recommendation`
- Input: metadata file
- Output: diagnosis, mapping, STG, and quality rule recommendations
- Use case: rule recommendation for governance landing

### `diagnosis_mapping_stg_quality_with_review`

- Stages: `diagnosis`, `mapping`, `stg`, `quality_rule_recommendation`, `review_replay`
- Input: metadata file
- Output: diagnosis, mapping, STG, quality rules, and confirmed results after local override replay
- Use case: quality recommendation rerun with historical human confirmation

### `mapping_only`

- Stages: `mapping`
- Input: metadata file
- Output: standard mapping recommendations only
- Use case: field standard recommendation validation

### `stg_only_from_mapping`

- Stages: `mapping`, `stg`
- Input: metadata file
- Output: mapping plus STG suggestions without full diagnosis packaging
- Use case: structure suggestion validation

### `quality_only_from_stg`

- Stages: `mapping`, `stg`, `quality_rule_recommendation`
- Input: metadata file
- Output: mapping, STG, and quality rule recommendations without full diagnosis packaging
- Use case: quality recommendation validation

## 4. Execution Mapping

The current router maps profiles to existing capabilities as follows:

- `metadata_diagnosis_only`
  - `run_p0_pipeline_from_file`
- `diagnosis_plus_mapping`
  - `run_p0_plus_mapping_from_file`
- `diagnosis_mapping_stg`
  - `run_p0_plus_mapping_plus_stg_from_file`
- `diagnosis_mapping_stg_with_review`
  - `run_p0_plus_mapping_plus_stg_with_review_from_file`
- `diagnosis_mapping_stg_quality`
  - `run_p0_plus_mapping_plus_stg_plus_quality_from_file`
- `diagnosis_mapping_stg_quality_with_review`
  - `run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file`
- `mapping_only`
  - lightweight mapping-only workflow based on current standard mapping skill
- `stg_only_from_mapping`
  - lightweight mapping + STG workflow based on current mapping and STG skills
- `quality_only_from_stg`
  - lightweight mapping + STG + quality workflow based on current downstream recommendation skills

## 5. Input and Output

Input is standardized through `GovernanceTaskRequest`.

Important fields:

- `file_path`
- `profile_name`
- `apply_review_replay`
- `export_reports`
- `output_dir`
- `base_filename`

Output is standardized through `GovernanceTaskResponse`.

Important fields:

- `profile_name`
- `status`
- `message`
- `stages_executed`
- `result`
- `exported_files`

## 6. Current Boundary

The current profile system is intentionally narrow:

- explicit user selection only
- rule-based routing only
- no natural-language intent recognition
- no autonomous planning
- no multi-agent coordination

## 7. Future Extension Notes

- TODO: add natural-language task understanding on top of profile routing
- TODO: add planner logic that can compose profiles from smaller tool stages
- TODO: expose profile metadata as agent-callable tool descriptors
