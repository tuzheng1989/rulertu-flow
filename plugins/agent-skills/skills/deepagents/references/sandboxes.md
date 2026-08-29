# Sandboxes - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/sandboxes

## Overview

Agents generate code, interact with filesystems, and run shell commands. Because we can't predict what an agent might do, it's important that its environment is isolated so it can't access credentials, files, or your host system. Sandboxes provide this isolation by creating a boundary between agent's execution environment and your host system.

In Deep Agents, __sandboxes are backends__ that define environment where agent operates. Unlike other backends (State, Filesystem, Store) which only expose file operations, sandbox backends also give agent an `execute` tool for running shell commands.

## Why use sandboxes?

Sandboxes are used for security. They let agents execute arbitrary code, access files, and use network without compromising your credentials, local files, or host system.

This isolation is essential when agents run autonomously. Sandboxes are especially useful for:

- Coding agents: Agents that run autonomously can use shell, git, clone repositories, and run Docker-in-Docker for build and test pipelines
- Data analysis agents: Load files, install data analysis libraries (pandas, numpy, etc.), run statistical calculations, and create outputs like PowerPoint presentations in a safe, isolated environment

## Basic usage

These examples assume you have already created a sandbox/devbox using the provider's SDK and have credentials set up. For signup, authentication, and provider-specific lifecycle details, see Available providers.

### Modal

```python
import modal
from langchain_anthropic import ChatAnthropic
from langchain_modal import ModalSandbox
from deepagents import create_deep_agent

app = modal.App.lookup("your-app")
modal_sandbox = modal.Sandbox.create(app=app)
backend = ModalSandbox(sandbox=modal_sandbox)

agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a small Python package and run pytest"
                }
            ]
        }
    )
finally:
    modal_sandbox.terminate()
```

### Runloop

```python
import os
from langchain_anthropic import ChatAnthropic
from langchain_runloop import RunloopSandbox
from runloop_api_client import RunloopSDK
from deepagents import create_deep_agent

client = RunloopSDK(bearer_token=os.environ["RUNLOOP_API_KEY"])
devbox = client.devbox.create()
backend = RunloopSandbox(devbox=devbox)

agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a small Python package and run pytest"
                }
            ]
        }
    )
finally:
    devbox.shutdown()
```

### Daytona

```python
from daytona import Daytona
from langchain_daytona import DaytonaSandbox
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent

nsandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=nsandbox)

agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a small Python package and run pytest"
                }
            ]
        }
    )
finally:
    sandbox.stop()
```

### LangSmith

```python
from langsmith.sandbox import SandboxClient
from deepagents.backends.langsmith import LangSmithSandbox
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent

client = SandboxClient()
ls_sandbox = client.create_sandbox(template_name="my-template")
backend = LangSmithSandbox(sandbox=ls_sandbox)

agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a small Python package and run pytest"
                }
            ]
        }
    )
finally:
    client.delete_sandbox(ls_sandbox.name)
```

### AgentCore

```python
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from langchain_agentcore_codeinterpreter import AgentCoreSandbox
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent

interpreter = CodeInterpreter(region="us-west-2")
interpreter.start()
backend = AgentCoreSandbox(interpreter=interpreter)

agent = create_deep_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a small Python package and run pytest"
                }
            ]
        }
    )
finally:
    interpreter.stop()
```

## The `execute` method

Sandbox backends implement the `execute()` method as the single method a provider must implement. Every other filesystem operation (`read`, `write`, `edit`, `ls`, `glob`, `grep`) is built on top of `execute()`.

The `execute` tool is conditionally available - the harness checks whether the backend implements `SandboxBackendProtocolV2`. When detected, it adds the `execute` tool to the agent's available tools.

```python
result = backend.execute("python --version")
print(result.output)
```

**Example output:**

```
4
[Command succeeded with exit code 0]

bash: foobar: command not found
[Command failed with exit code 127]
```

If a command produces very large output, the result is automatically saved to a file and the agent is instructed to use `read_file` to access it incrementally.

## Two planes of file access

There are two distinct ways files move in and out of a sandbox:

### Agent filesystem tools

- `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`
- Called by LLM during agent execution
- Operate through `execute()` under the hood
- Input and output are in the sandbox

### File transfer APIs

Application code calls these directly:

- `upload_files()`: Seed sandbox with files before agent runs
- `download_files()`: Retrieve artifacts after agent finishes

These use provider-specific APIs for efficient file transfer.

**Seeding a sandbox:**
```python
from daytona import Daytona
from langchain_daytona import DaytonaSandbox

nsandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=nsandbox)

# Upload files before agent runs
backend.upload_files([
    ("/src/index.py", b"print('Hello')\n"),
    ("/pyproject.toml", b"[project]\nname = 'my-app'\n"),
])

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=backend,
    system_prompt="You are a coding assistant. The code is available at /src/index.py.",
)
```

**Retrieving artifacts:**
```python
# Download files after agent finishes
results = backend.download_files(["/output.txt", "/src/index.py"])

for result in results:
    if result.content is not None:
        print(f"{result.path}: {result.content.decode()}")
    else:
        print(f"Failed to download {result.path}: {result.error}")
```

## Lifecycle and scoping

How you manage sandbox lifecycle depends on your application.

### Thread-scoped (default)

Each conversation gets its own sandbox. The sandbox is created when first run starts and reused for follow-up messages. When the thread ends (or sandbox TTL expires), the sandbox is destroyed.

This is the right default for most agents. Use when each conversation starts with a clean environment.

### Assistant-scoped

All threads for a given assistant share one sandbox. The sandbox ID is stored on the assistant's configuration. Every conversation with that assistant returns to the same environment.

Use this when an agent maintains a long-running workspace (e.g., a code base, installed dependencies).

### Basic lifecycle

For each provider, you're responsible for creating and destroying the sandbox:

**Lifecycle operations:**

1. `create()` / `devbox.create()`
2. Run agent with the sandbox
3. Call `destroy()` / `devbox.delete()` / `client.delete_sandbox()`

The sandbox consumes resources until it's shut down.

### Per-conversation lifecycle

In chat applications, a conversation is typically represented by a `thread_id`. Store the mapping between sandbox ID and `thread_id` in your application or with sandbox metadata if the provider allows it.

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
    system_prompt="You are a coding assistant with sandbox access.",
)
```

For other providers, consult the sandbox provider API for equivalent labels, metadata, and TTL options.

## Integration patterns

### Agent in sandbox pattern

The agent runs inside the sandbox and you communicate with it over the network.

**Benefits:**
- ✅ Mirrors local development closely
- ✅ Tight coupling between agent and environment
- ✅ Consistent execution environment

**Trade-offs:**
- 🔴 API keys must live inside sandbox (security risk)
- 🔴 Updates require rebuilding images
- 🔴 Requires infrastructure for communication (WebSocket or HTTP layer)

To run an agent in a sandbox, build an image and install deepagents on it:

```dockerfile
FROM python:3.11
RUN pip install deepagents-cli

# Run agent
CMD ["python", "-m", "agent", "serve", "--host", "0.0.0.0"]
```

### Sandbox as tool pattern

The agent runs on your machine or server. When it needs to execute code, it calls sandbox tools via network.

**Benefits:**
- ✅ Update agent code instantly without rebuilding images
- ✅ Cleaner separation between agent state and execution
  - API keys stay outside sandbox
  - Sandbox failures don't lose agent state
  - Option to run tasks in multiple sandboxes in parallel
- ✅ Pay only for execution time

**Trade-offs:**
- 🔴 Network latency on each execution call
- 🔴 Agent can't access local files directly

## Security considerations

Sandboxes isolate code execution from your host system, but they don't protect against everything:

### What sandboxes don't protect

- **Context injection**: An attacker who controls part of agent's input can instruct it to run arbitrary commands inside the sandbox. The sandbox is isolated, but the agent has full control within it.
- **Network exfiltration**: Unless network access is blocked, a context-injected agent can send data out of the sandbox over HTTP or DNS.

### Handling secrets safely

If your agent needs to call authenticated APIs or access protected resources:

**Option 1: Keep secrets in tools outside sandbox**

Define tools that run in your host environment:

```python
from langchain.tools import tool

@tool
def api_call(api_key: str, query: str) -> str:
    """Call external API from host machine."""
    import requests
    response = requests.post(
        "https://api.example.com/query",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query}
    )
    return response.json()

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[api_call],  # Agent can use this tool
)
```

The agent never sees the API key — only the tool result.

**Option 2: Use network proxy**

Some sandbox providers support HTTP proxies that intercept outgoing requests and inject credentials:

```python
from deepagents.backends import ProtocolBackend

class ProxyBackend(BackendProtocol):
    def __init__(self, inner: BackendProtocol, secret: str):
        self.inner = inner
        self.secret = secret

    def write(self, file_path: str, content: str):
        # Intercept write operations and inject secret
        content = content.replace("${SECRET}", self.secret)
        return self.inner.write(file_path, content)
```
```

### General best practices

- Review sandbox outputs before acting on them in your application
- Block sandbox network access when not needed
- Treat everything produced inside the sandbox as untrusted input
- Rotate credentials regularly
- Use separate API keys for development vs production
- Consider using rate limiting on API calls made by agents

## Isolation boundaries

| Boundary | Protected | Accessible |
| --- | --- | --- |
| Your host system | ✅ Protected | ❌ No access |
| Sandbox filesystem | ✅ Isolated | ✅ Protected |
| Shell commands | ❌ Blocked | ✅ Available |
| Network | ⚠️️ Proxy control | ⚠️️️️️️ Risk of exfiltration |
| API calls | ❌ Via proxy only | ❌ Via tools |

Use sandboxes when you need code execution in isolation. For file access without code execution, use FilesystemBackend or StoreBackend.
