## Tool Contract Layer

### Positioning

The tool contract layer exposes the current local governance capabilities through a
stable, explicit, and auditable interface.

It is meant to sit above:

- workflow profiles
- governance task router
- intent interpreter
- agent shell
- context resolver

It is not:

- an MCP server
- an OpenAI tool-calling runtime
- an external agent framework adapter

### Why This Layer Exists

The project already has multiple runnable services and workflows. Without a shared
tool contract, upper layers would need to call internal modules directly and handle
inconsistent payload shapes.

The tool contract layer provides:

- standard tool definitions
- explicit input and output schema names
- one unified local executor
- local execution traces for audit and replay analysis

### Relationship to Existing Components

- `workflow profiles` define what workflow should run
- `governance router` executes a structured workflow request
- `intent interpreter` converts natural language into a structured request
- `agent shell` adds preview, validation, and confirmation-aware execution
- `context resolver` autofills safe missing parameters
- `tool executor` wraps these abilities as standard local tools
- `trace store` records what was called and what happened

### Supported Tools

#### 1. `run_governance_profile`

- input: `GovernanceTaskRequest`
- output: `GovernanceTaskResponse`
- use case: run an explicit workflow profile directly

#### 2. `interpret_governance_intent`

- input: `text`, `file_path` optional
- output: interpreted intent plus built `GovernanceTaskRequest`
- use case: convert natural language into a standard task request without running

#### 3. `preview_agent_plan`

- input: `text`, `file_path` optional, `session_id` optional
- output: `AgentShellResult`
- use case: preview plan, validation state, confirmation requirement, and context autofill

#### 4. `run_agent_task`

- input: `text`, `file_path` optional, `session_id` optional, `force_run` optional
- output: `AgentShellResult`
- use case: natural language plus conditional execution through the agent shell

#### 5. `resolve_governance_context`

- input: `text`, `file_path` optional, `session_id` optional
- output: resolved context plus execution plan summary
- use case: inspect context autofill and plan state without committing to execution

#### 6. `export_governance_reports`

- input: `profile_name`, `result`, `output_dir` optional, `base_filename` optional
- output: exported file paths
- use case: export JSON, Markdown, and Excel reports from a known workflow result

#### 7. `recommend_quality_rules`

- input: `QualityRuleToolRequest`
- output: `GovernanceTaskResponse`
- use case: run the governance chain up to quality rule recommendation for downstream review or integration

#### 8. `list_config_assets`

- input: optional empty payload
- output: managed asset list with current status
- use case: inspect which governance configuration assets are under control-plane management

#### 9. `get_config_asset`

- input: `asset_name`
- output: asset metadata, status, format, and current content
- use case: inspect one managed YAML, JSON, or CSV asset before editing

#### 10. `validate_config_asset`

- input: `asset_name`
- output: `ValidationResult`
- use case: validate the current saved version of one managed asset

#### 11. `save_config_asset`

- input: `asset_name`, `content`
- output: `ConfigEditResult`
- use case: validate, back up, and save one managed asset through the tool layer

#### 12. `publish_config_asset`

- input: `asset_name`
- output: `ConfigEditResult`
- use case: mark one validated managed asset as published

### Tool Execution Flow

The standard execution flow is:

1. resolve tool definition from registry
2. validate minimal arguments
3. call the existing internal service or router
4. normalize result into `ToolCallResponse`
5. persist one `ExecutionTrace`

### Execution Trace

Each tool call should generate a local trace that includes:

- tool name
- session id when available
- raw text when available
- profile name when available
- summarized inputs
- resolved context summary when available
- stages executed when available
- status and message
- config asset name and operation for control-plane tool calls
- validation status for config asset operations when available
- exported files when available

This trace is for:

- local audit
- debugging
- replay analysis
- later adapter integration

### Current Boundary

Current scope is intentionally limited:

- local tool layer only
- rule-based only
- single-user only
- local JSON trace storage only
- no external tool runtime integration
- no LLM-based tool arbitration

### Future Direction

Later versions may add:

- MCP adapter
- OpenAI tool-calling adapter
- external orchestration runtime adapter
- richer trace analytics and filtering
