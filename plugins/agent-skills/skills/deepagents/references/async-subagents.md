# Async Subagents - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/async-subagents

## Overview

Async subagents let a supervisor agent launch background tasks that return immediately, so supervisor can continue interacting with the user while subagents work concurrently. The supervisor can check progress, send follow-up instructions, or cancel tasks at any point.

This builds on subagents, which run synchronously and block the supervisor until completion. Use async subagents when tasks are long-running, parallelizable, or need mid-flight steering.

## When to use async subagents

| Dimension | Sync subagents | Async subagents |
| --- | --- | --- |
| **Execution model** | Supervisor blocks until subagent completes | Returns job ID immediately; supervisor continues |
| **Concurrency** | Parallel but blocking | Parallel and non-blocking |
| **Mid-task updates** | Not possible | Send follow-up instructions via `update_async_task` |
| **Cancellation** | Not possible | Cancel running tasks via `cancel_async_task` |
| **Statefulness** | Stateless — no persistent state between invocations | Stateful — maintains state on its own thread across interactions |
| **Best for** | Tasks where agent should wait for results before continuing | Long-running, complex tasks managed interactively in a chat |

## Configure async subagents

Define async subagents as a list of `AsyncSubAgent` specs, each pointing to an Agent Protocol server:

```python
from deepagents import AsyncSubAgent, create_deep_agent

async_subagents = [
    AsyncSubAgent(
        name="researcher",
        description="Research agent for information gathering and synthesis",
        graph_id="researcher",
        # No url → ASGI transport (co-deployed in the same deployment)
    ),
    AsyncSubAgent(
        name="coder",
        description="Coding agent for code generation and review",
        graph_id="coder",
        # url="https://coder-deployment.langsmith.dev"  # Optional: HTTP transport for remote
    ),
]

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    subagents=async_subagents,
)
```

| Field | Type | Description |
| --- | --- | --- |
| `name` | `str` | Required. Unique identifier. The supervisor uses this when launching tasks. |
| `description` | `str` | Required. What this subagent does. The supervisor uses this to decide which agent to delegate to. |
| `graph_id` | `str` | Required. The graph ID (or assistant ID) on the Agent Protocol server. For LangGraph-based deployments, this must match a graph registered in `langgraph.json`. |
| `url` | `str` \| `None` | Optional. When omitted, uses ASGI transport (in-process). When set, uses HTTP transport to a remote Agent Protocol server. |
| `headers` | `dict[str, str]` \| `None` | Optional. Additional headers for requests to remote server. Use for custom authentication with self-hosted Agent Protocol servers. |

For LangGraph-based deployments, register all graphs in the same `langgraph.json` for co-deployed setups:

```json
{
  "graphs": {
    "supervisor": "./src/supervisor.py:graph",
    "researcher": "./src/researcher.py:graph",
    "coder": "./src/coder.py:graph"
  }
}
```

The `AsyncSubAgentMiddleware` gives the supervisor five tools:

| Tool | Purpose | Returns |
| --- | --- | --- |
| `start_async_task` | Start a new background task | Task ID (immediately) |
| `check_async_task` | Get current status and result of a task | Status + result (if complete) |
| `update_async_task` | Send new instructions to a running task | Confirmation + updated status |
| `cancel_async_task` | Stop a running task | Confirmation |
| `list_async_tasks` | List all tracked tasks with live statuses | Summary of all tasks |

The supervisor's LLM calls these tools like any other tool. The middleware handles thread creation, run management, and state persistence automatically.

## Understand lifecycle

A typical interaction follows this sequence:

- **Launch** creates a new thread on the server, starts a run with the task description as input, and returns the thread ID as the task ID. The supervisor reports this ID to the user and does not poll for completion.
- **Check** fetches the current run status. If the run succeeded, it retrieves the thread state to extract the subagent's final output. If still running, it reports that to the user.
- **Update** creates a new run on the same thread with an interrupt multitask strategy. The previous run is interrupted, and the subagent restarts with the full conversation history plus the new instructions. The task ID stays the same.
- **Cancel** calls `runs.cancel()` on the server and marks the task as `"cancelled"`.
- **List** iterates over all tracked tasks. For non-terminal tasks, it fetches live status from the server in parallel. Terminal statuses (`"success"`, `"error"`, `"cancelled"`) are returned from cache.

## Understand state management

Task metadata is stored in a dedicated state channel (`async_tasks`) on the supervisor's graph, separate from the message history. This is critical because deep agents compact their message history when the context window fills up. If task IDs were only in tool messages, they would be lost during compaction.

Each tracked task records task ID, agent name, thread ID, run ID, status, and timestamps (`created_at`, `last_checked_at`, `last_updated_at`).

## Choose a transport

### ASGI transport (co-deployed)

When a subagent spec omits the `url` field, LangGraph SDK uses ASGI transport — SDK calls are routed through in-process function calls rather than HTTP. For LangGraph-based deployments, this requires both graphs to be registered in the same `langgraph.json`.

ASGI transport eliminates network latency and requires no additional auth configuration. The subagent still runs as a separate thread with its own state. This is the recommended default.

### HTTP transport (remote)

Add a `url` field to switch to HTTP transport, where SDK calls go over the network to a remote Agent Protocol server:

```python
AsyncSubAgent(
    name="researcher",
    description="Research agent",
    graph_id="researcher",
    url="https://my-research-deployment.langsmith.dev",
)
```

For LangGraph deployments, authentication is handled by the LangGraph SDK using `LANGSMITH_API_KEY` (or `LANGGRAPH_API_KEY`) from environment variables. Self-hosted Agent Protocol servers may use a different authentication mechanism.

Use HTTP transport when subagents need different compute profiles or independent scaling.

## Choose a deployment topology

### Single deployment

A single deployment means all agents are co-deployed on the same server using ASGI transport. For LangGraph-based deployments, register all graphs in one `langgraph.json`. This is the recommended starting point — one server to manage, zero network latency between agents.

### Split deployment

Supervisor on one server, subagents on another via HTTP transport. Use when subagents need different compute profiles or independent scaling.

### Hybrid

In a split deployment, some subagents are co-deployed via ASGI, others remote via HTTP:

```python
async_subagents = [
    AsyncSubAgent(
        name="researcher",
        description="Research agent",
        graph_id="researcher",
        # No url → ASGI (co-deployed)
    ),
    AsyncSubAgent(
        name="coder",
        description="Coding agent",
        graph_id="coder",
        url="https://coder-deployment.langsmith.dev",  # HTTP (remote)
    ),
]
```

## Lifecycle and scoping

Sandboxes consume resources and cost money until they're shut down. How you manage their lifecycle depends on your application.

### Thread-scoped (default)

Each conversation gets its own sandbox. The sandbox is created when the first run starts and reused for follow-up messages on the same thread. When the thread is cleaned up (or the sandbox TTL expires), the sandbox is destroyed.

This is the right default for most agents.

### Assistant-scoped

All threads for a given assistant share one sandbox. The sandbox ID is stored on the assistant's configuration, so every conversation returns to the same environment. Files, installed packages, and cloned repositories persist across conversations.

Use this when the agent maintains a long-running workspace.

### Basic lifecycle

For each provider, you're responsible for creating and destroying the sandbox:

**Daytona:**
```python
from daytona import Daytona
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

sandbox = Daytona().create()
agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=DaytonaSandbox(sandbox=sandbox),
)
try:
    result = agent.invoke(...)
finally:
    sandbox.stop()
```

**Modal:**
```python
import modal
from langchain_modal import ModalSandbox

app = modal.App.lookup("your-app")
modal_sandbox = modal.Sandbox.create(app=app)
backend = ModalSandbox(sandbox=modal_sandbox)
agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)
try:
    result = agent.invoke(...)
finally:
    modal_sandbox.terminate()
```

**Runloop:**
```python
from runloop_api_client import RunloopSDK
from langchain_runloop import RunloopSandbox

client = RunloopSDK(bearer_token="...")
devbox = client.devbox.create()
backend = RunloopSandbox(devbox=devbox)
agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)
try:
    result = agent.invoke(...)
finally:
    devbox.shutdown()
```

**AgentCore:**
```python
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from langchain_agentcore_codeinterpreter import AgentCoreSandbox

interpreter = CodeInterpreter(region="us-west-2")
interpreter.start()
backend = AgentCoreSandbox(interpreter=interpreter)
agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)
try:
    result = agent.invoke(...)
finally:
    interpreter.stop()
```

**LangSmith:**
```python
from langsmith.sandbox import SandboxClient
from deepagents.backends.langsmith import LangSmithSandbox

client = SandboxClient()
ls_sandbox = client.create_sandbox(template_name="my-template")
backend = LangSmithSandbox(sandbox=ls_sandbox)
agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)
try:
    result = agent.invoke(...)
finally:
    client.delete_sandbox(ls_sandbox.name)
```

### Per-conversation lifecycle

In chat applications, a conversation is typically represented by a `thread_id`. Generally, each `thread_id` should use its own unique sandbox.

Store the mapping between sandbox ID and `thread_id` in your application or with the sandbox if the sandbox provider allows attaching metadata to the sandbox.

```python
from langchain_core.utils.uuid import uuid7
from daytona import CreateSandboxFromSnapshotParams, Daytona
from deepagents import create_deep_agent
from langchain_daytona import DaytonaSandbox

client = Daytona()
thread_id = str(uuid7())

# Get or create sandbox by thread_id
try:
    sandbox = client.find_one(labels={"thread_id": thread_id})
except Exception:
    params = CreateSandboxFromSnapshotParams(
        labels={"thread_id": thread_id},
        # Add TTL so sandbox is cleaned up when idle
        auto_delete_interval=3600,
    )
    sandbox = client.create(params)

backend = DaytonaSandbox(sandbox=sandbox)
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=backend,
    system_prompt="You are a coding assistant with sandbox access. You can create and run code in sandbox.",
)
try:
    result = agent.invoke(...)
except Exception:
    # Optional: delete sandbox proactively on an exception
    client.delete(sandbox)
    raise
```

For other providers, consult the sandbox provider API for equivalent labels, metadata, and TTL options.

## Best practices

### Size worker pool for local development

When running locally with `langgraph dev`, increase the worker pool to accommodate concurrent subagent runs. Each active run occupies a worker slot. A supervisor with 3 concurrent subagent tasks requires 4 slots (1 supervisor + 3 subagents). Under-provisioning causes launches to queue.

```bash
langgraph dev --n-jobs-per-worker 10
```

### Write clear subagent descriptions

The supervisor uses descriptions to decide which subagent to launch. Be specific and action-oriented:

```python
# Good
AsyncSubAgent(
    name="researcher",
    description="Conducts in-depth research using web search. Use for questions requiring multiple searches and synthesis.",
    graph_id="researcher",
)
# Bad
AsyncSubAgent(
    name="helper",
    description="helps with stuff",
    graph_id="helper",
)
```

### Trace with thread IDs

When using LangGraph-based deployments, every async subagent run is a standard LangGraph run, fully visible in LangSmith. The supervisor's trace shows tool calls for `launch`, `check`, `update`, `cancel`, and `list`. Each subagent run appears as a separate trace, linked by thread ID. Use the thread ID (task ID) to correlate supervisor orchestration traces with subagent execution traces.

## Troubleshooting

### Supervisor polls immediately after launch

**Problem**: The supervisor calls `check` in a loop right after launching, turning async execution into blocking.

**Solution**: The middleware injects system prompt rules to prevent this. If polling persists, reinforce the behavior in your supervisor's system prompt:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    system_prompt="""...your instructions...
    After launching an async subagent, ALWAYS return control to the user.
    Never call check_async_task immediately after launch.""",
    subagents=async_subagents,
)
```

### Supervisor reports stale status

**Problem**: The supervisor references a task status from earlier in conversation history instead of making a fresh `check` call.

**Solution**: The middleware prompt instructs the model that "task statuses in conversation history are always stale." If this still occurs, add explicit instructions to always call `check` or `list` before reporting status.

### Task ID lookup failures

**Problem**: The supervisor truncates or reformats the task ID, causing `check` or `cancel` to fail.

**Solution**: The middleware prompt instructs the model to always use the full task ID. If truncation persists, this is typically a model-specific issue — try a different model or add "always show the full task_id, never truncate or abbreviate it" to your system prompt.

### Subagent launches queue instead of running

**Problem**: Launching a subagent hangs or takes a long time to start.

**Solution**: The worker pool is likely exhausted. Increase pool size with `--n-jobs-per-worker`. See Size worker pool.
