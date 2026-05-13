## Context Resolver

### Positioning

The context resolver is a rule-based parameter autofill layer for the local agent shell.
It does not change workflow intent, and it does not introduce LLM reasoning.
Its job is to reduce avoidable execution failures caused by missing context parameters,
especially `file_path`.

### Relationship to Existing Components

- `intent_interpreter` maps natural-language task text to a workflow profile.
- `context_resolver` fills missing execution parameters from safe local context.
- `execution_planner` validates the resolved task request and builds a previewable plan.
- `session_store` provides the recent local context used for autofill.

The execution flow is:

1. interpret task text
2. build initial `GovernanceTaskRequest`
3. resolve context and autofill safe parameters
4. build execution plan
5. preview or execute

### Supported Context Sources

Current version supports these context sources:

1. explicit `file_path` passed by caller
2. `session.last_uploaded_file_path`
3. `session.last_task_request.file_path`
4. `session.last_exported_files`
5. local sample file fallback when explicitly enabled by config

### Supported Reference Expressions

Current file reference examples:

- `this file`
- `current file`
- `uploaded file`
- `last file`
- `previous file`
- `这个文件`
- `当前文件`
- `刚上传的文件`
- `上一个文件`
- `上次文件`

Current result reference examples:

- `last result`
- `previous result`
- `latest report`
- `上一次结果`
- `最近一次结果`
- `最新报告`

### Autofill Priority

The current `file_path` priority is:

1. explicit `file_path`
2. `session.last_uploaded_file_path`
3. `session.last_task_request.file_path`
4. sample file fallback when enabled

The resolver will not override an explicit `file_path`.

### Ambiguity Handling

The resolver remains conservative:

- if there is one safe candidate, it may autofill
- if multiple conflicting candidates exist and the reference is not clear enough, it does not guess
- ambiguity is returned in `ResolvedContext` and surfaced in execution plan messages

### Output

The resolver returns:

- resolved `GovernanceTaskRequest`
- `ResolvedContext`
- whether resolution was applied

The execution plan must show:

- which parameters were autofilled
- where the value came from
- whether ambiguity blocked autofill

### Current Boundary

Current scope is intentionally limited:

- rule-based only
- session-scoped only
- local single-user only
- no semantic retrieval
- no file search
- no complex reference disambiguation
- no LLM-assisted completion

### Future Direction

Later versions may add:

- local file search
- stronger session history ranking
- richer result-reference continuation
- optional LLM-assisted parameter completion after explicit user approval
