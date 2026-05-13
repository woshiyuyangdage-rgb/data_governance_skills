## Adapter Layer v1

### Positioning

The adapter layer prepares the current local governance tool platform for future
external integration without changing the existing workflow, tool, or control-plane
boundaries.

It sits on top of the current tool contract layer and exposes three things:

- capability manifest
- tool schema export
- local invocation adapter

### Relationship to the Tool Contract Layer

The tool contract layer is the execution surface for local tools.

The adapter layer does not replace it. Instead, it:

- reads tool definitions from the current tool registry
- converts them into more standard exported schemas
- provides a thin adapter for alternate local invocation shapes

### Current Capabilities

#### 1. Capability Manifest

The adapter layer can generate one structured manifest that describes:

- service identity
- version
- description
- available tools

#### 2. Tool Schema Export

The adapter layer can export current tools in three local formats:

- native tool schema
- openai-style function schema
- mcp-style lightweight manifest

Current native schema focuses on explicit readability and includes:

- tool name
- description
- category
- input model name
- output model name
- simplified input schema
- simplified output schema

#### 3. Local Invocation Adapter

The adapter layer can accept multiple local invocation shapes and forward them to
the existing tool layer, including:

- native tool invocation
- openai-style function invocation
- manifest-style tool invocation

### What This Layer Does Not Do

Current scope explicitly excludes:

- real MCP server transport
- external SDK integration
- remote authentication
- remote execution routing
- protocol-complete interoperability work

### Why This Layer Exists

The current project already has:

- a tool registry
- a local tool executor
- execution traces
- a control plane

That is enough to become adapter-ready, but not yet enough to expose a clean
integration contract for future external runtimes.

This adapter layer creates that preparation step without introducing network or
platform complexity.

### Future Extension Direction

Later versions may add:

- MCP transport adapter
- OpenAI tool-calling binding
- external orchestration runtime integration
- remote execution gateway
