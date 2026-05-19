"""Agent shell, tool adapter, and trace entries for the jobs catalog."""

TOOL_JOB_ITEMS = [
    {
        "name": "agent_shell_plan",
        "method": "POST",
        "path": "/jobs/agent-shell/plan",
        "description": "Interpret task text and return a previewable execution plan without running it.",
    },
    {
        "name": "agent_shell_resolve_context",
        "method": "POST",
        "path": "/jobs/agent-shell/resolve-context",
        "description": "Interpret task text, resolve local session context, and return the resolved plan without executing it.",
    },
    {
        "name": "agent_shell_run",
        "method": "POST",
        "path": "/jobs/agent-shell/run",
        "description": "Interpret task text, build a plan, and execute only when validation and confirmation policy allow it.",
    },
    {
        "name": "agent_shell_session",
        "method": "GET",
        "path": "/jobs/agent-shell/session/{session_id}",
        "description": "Return a lightweight agent shell session overview.",
    },
    {
        "name": "list_tools",
        "method": "GET",
        "path": "/jobs/list-tools",
        "description": "Return enabled tool contract definitions for the local tool layer.",
    },
    {
        "name": "call_tool",
        "method": "POST",
        "path": "/jobs/call-tool",
        "description": "Call one local governance tool through the standardized tool executor.",
    },
    {
        "name": "capability_manifest",
        "method": "GET",
        "path": "/jobs/capability-manifest",
        "description": "Return the adapter-layer capability manifest for local external integration preparation.",
    },
    {
        "name": "tool_schemas_native",
        "method": "GET",
        "path": "/jobs/tool-schemas/native",
        "description": "Return native tool schemas exported from the local tool registry.",
    },
    {
        "name": "tool_schemas_openai",
        "method": "GET",
        "path": "/jobs/tool-schemas/openai",
        "description": "Return simplified OpenAI-style function schemas for local adapter use.",
    },
    {
        "name": "tool_schemas_mcp",
        "method": "GET",
        "path": "/jobs/tool-schemas/mcp",
        "description": "Return a lightweight MCP-style manifest for local adapter inspection.",
    },
    {
        "name": "invoke_native_tool",
        "method": "POST",
        "path": "/jobs/invoke-native-tool",
        "description": "Invoke one local governance tool through the native adapter shape.",
    },
    {
        "name": "invoke_openai_tool",
        "method": "POST",
        "path": "/jobs/invoke-openai-tool",
        "description": "Invoke one local governance tool through the simplified OpenAI-style adapter shape.",
    },
    {
        "name": "get_trace",
        "method": "GET",
        "path": "/jobs/trace/{trace_id}",
        "description": "Return one execution trace by trace id.",
    },
    {
        "name": "list_recent_traces",
        "method": "GET",
        "path": "/jobs/traces/recent",
        "description": "Return recent execution traces from the local audit store.",
    },
]
