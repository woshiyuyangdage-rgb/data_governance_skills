# Agent Shell Specification

## 1. Positioning

Agent Shell v1 is a controlled governance execution assistant.

It is not a chat agent. It does not reason freely, plan autonomously, or hold complex conversational memory.

Its role is to add one more structured layer above the existing intent interpreter and governance router:

- interpret task text
- build an execution plan
- validate required parameters
- preview the plan
- require confirmation when policy says so
- run only when allowed

## 2. Relationship to Existing Components

The current stack is:

1. `IntentInterpreter`
   - converts natural language into `InterpretedIntent` and `GovernanceTaskRequest`
2. `ExecutionPlanner`
   - converts interpreted intent plus task request into `ExecutionPlan`
3. `GovernanceTaskRouter`
   - executes the standardized workflow request
4. `AgentShellService`
   - coordinates interpretation, planning, validation, confirmation, execution, and session state

## 3. Supported Capabilities

Agent Shell v1 supports:

- interpret
- build execution plan
- validate parameters
- preview before run
- confirmation-aware execution
- force run when explicitly allowed by the caller

## 4. Unsupported Capabilities

Agent Shell v1 does not support:

- LLM reasoning
- multi-turn planning
- autonomous replanning
- open-ended dialogue management
- tool-selection by free-form reasoning

## 5. Core Structures

### Execution Plan

The plan includes:

- raw request text
- selected profile
- planned stages
- whether review replay or report export is enabled
- whether confirmation is required
- whether validation passed
- validation messages
- suggested output mode
- human-readable summary

### Agent Session

The session stores:

- session id
- recent request texts
- recent plans
- last task request
- last task response

This is intentionally lightweight and local.

## 6. Current Boundary

The current shell is:

- rule-based
- local
- single-user
- session-light
- preview-first

It is meant to be a stable shell for future planner upgrades, not a full agent runtime.

## 7. Future Extension Notes

- TODO: replace rule-based interpretation with optional LLM intent parsing
- TODO: add multi-turn parameter completion for missing file path or export choices
- TODO: allow future planner layers to revise or branch plans before execution
- TODO: expose shell plans to future tool-calling agents without changing current workflow contracts
