# Customization - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/customization

## Overview

`create_deep_agent` has the following core configuration options:

- Model
- Tools
- System Prompt
- Middleware
- Subagents
- Backends (virtual filesystems)
- Human-in-the-loop
- Skills
- Memory

```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    response_format: ResponseFormat[ResponseT] | type[ResponseT] | dict[str, Any] | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    ...
) -> CompiledStateGraph
```

For the full parameter list, see the `create_deep_agent` API reference.

## Model

Pass a `model` string in `provider:model` format, or an initialized model instance. Defaults to `anthropic:claude-sonnet-4-6`. See [[models.md]] for all providers and suggested models for tested recommendations.

- OpenAI
- Anthropic
- Azure
- Google Gemini
- AWS Bedrock
- HuggingFace
- Other

### Connection resilience

LangChain chat models automatically retry failed API requests with exponential backoff. By default, models retry up to **6 times** for network errors, rate limits (429), and server errors (5xx). Client errors like 401 (unauthorized) or 404 are not retried.

You can adjust the `max_retries` parameter when creating a model to tune this behavior for your environment:

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=init_chat_model(
        model="google_genai:gemini-3.1-pro-preview",
        max_retries=10,  # Increase for unreliable networks (default: 6)
        timeout=120,     # Increase timeout for slow connections
    ),
)
```

## Tools

In addition to the built-in tools for planning, file management, and subagent spawning, you can provide custom tools:

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[internet_search]
)
```

## System prompt

Deep Agents come with a built-in system prompt. The default system prompt contains detailed instructions for using the built-in planning tool, file system tools, and subagents. When middleware adds special tools, like filesystem tools, it appends them to the system prompt.

Each deep agent should also include a custom system prompt specific to its specific use case:

```python
from deepagents import create_deep_agent

research_instructions = """
You are an expert researcher. Your job is to conduct
thorough research, and then write a polished report.
"""

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    system_prompt=research_instructions,
)
```

## Middleware

By default, Deep Agents have access to the following middleware:

- `TodoListMiddleware`: Tracks and manages todo lists for organizing agent tasks and work
- `FilesystemMiddleware`: Handles file system operations such as reading, writing, and navigating directories
- `SubAgentMiddleware`: Spawns and coordinates subagents for delegating tasks to specialized agents
- `SummarizationMiddleware`: Condenses message history to stay within context limits when conversations grow long
- `AnthropicPromptCachingMiddleware`: Automatic reduction of redundant token processing when using Anthropic models
- `PatchToolCallsMiddleware`: Automatic message history fixes when tool calls are interrupted or cancelled before receiving results

If you are using memory, skills, or human-in-the-loop, the following middleware is also included:

- `MemoryMiddleware`: Persists and retrieves conversation context across sessions when the `memory` argument is provided
- `SkillsMiddleware`: Enables custom skills when the `skills` argument is provided
- `HumanInTheLoopMiddleware`: Pauses for human approval or input at specified points when the `interruptOn` argument is provided

### Pre-built middleware

LangChain exposes additional pre-built middleware that let you add-on various features, such as retries, fallbacks, or PII detection. See Prebuilt middleware for more.

The `deepagents` library also exposes `create_summarization_tool_middleware`, enabling agents to trigger summarization at opportune times—such as between tasks—instead of at fixed token intervals. For more detail, see [[context-engineering.md]].

### Provider-specific middleware

For provider-specific middleware that is optimized for specific LLM providers, see Official integrations and Community integrations.

### Custom middleware

You can provide additional middleware to extend functionality, add tools, or implement custom hooks:

```python
from langchain.tools import tool
from langchain.agents.middleware import wrap_tool_call
from deepagents import create_deep_agent

@tool
def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is sunny."

call_count = [0]  # Use list to allow modification in nested function

@wrap_tool_call
def log_tool_calls(request, handler):
    """Intercept and log every tool call - demonstrates cross-cutting concern."""
    call_count[0] += 1
    tool_name = request.name if hasattr(request, 'name') else str(request)
    print(f"[Middleware] Tool call #{call_count[0]}: {tool_name}")
    print(f"[Middleware] Arguments: {request.args if hasattr(request, 'args') else 'N/A'}")

    # Execute the tool call
    result = handler(request)

    # Log the result
    print(f"[Middleware] Tool call #{call_count[0]} completed")
    return result

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[get_weather],
    middleware=[log_tool_calls],
)
```

## Subagents

To isolate detailed work and avoid context bloat, use subagents:

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "openai:gpt-5.2",  # Optional override, defaults to main agent model
}

subagents = [research_subagent]

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    subagents=subagents
)
```

For more information, see [[subagents.md]] and [[async-subagents]].

## Backends

Deep agent tools can make use of virtual file systems to store, access, and edit files. By default, Deep Agents use a `StateBackend`.

If you are using skills or memory, you must add the expected skill or memory files to the backend before creating the agent.

- StateBackend
- FilesystemBackend
- LocalShellBackend
- StoreBackend
- CompositeBackend

### StateBackend

An ephemeral filesystem backend stored in `langgraph` state. This filesystem only persists **for a single thread**.

```python
# By default we provide a StateBackend
agent = create_deep_agent(model="google_genai:gemini-3.1-pro-preview")

# Under the hood, it looks like
from deepagents.backends import StateBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=StateBackend()
)
```

### FilesystemBackend

The local machine's filesystem.

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=FilesystemBackend(root_dir=".", virtual_mode=True)
)
```

### LocalShellBackend

A filesystem with shell execution directly on the host. Provides filesystem tools plus an `execute` tool for running commands.

```python
from deepagents.backends import LocalShellBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=LocalShellBackend(root_dir=".", env={"PATH": "/usr/bin:/bin"})
)
```

### StoreBackend

A filesystem that provides long-term storage that is **persisted across threads**.

```python
from langgraph.store.memory import InMemoryStore
from deepagents.backends import StoreBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=StoreBackend(
        namespace=lambda ctx: (ctx.runtime.context.user_id,),
    ),
    store=InMemoryStore()  # Good for local dev; omit for LangSmith Deployment
)
```

### CompositeBackend

A flexible backend where you can specify different routes in the filesystem to point towards different backends.

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(),
        }
    ),
    store=InMemoryStore()  # Store passed to create_deep_agent, not backend
)
```

For more information, see [[backends.md]].

### Sandboxes

Sandboxes are specialized backends that run agent code in an isolated environment with their own filesystem and an `execute` tool for shell commands.

Use a sandbox backend when you want your deep agent to write files, install dependencies, and run commands without changing anything on your local machine.

You configure sandboxes by passing a sandbox backend to `backend` when creating your deep agent:

- Modal
- Runloop
- Daytona
- LangSmith

```python
# Modal
import modal
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
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
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Create a small Python package and run pytest",
                }
            ]
        }
    )
finally:
    modal_sandbox.terminate()
```

```python
# Runloop
import os
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_runloop import RunloopSandbox
from runloop_api_client import RunloopSDK

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
                    "content": "Create a small Python package and run pytest",
                }
            ]
        }
    )
finally:
    devbox.shutdown()
```

```python
# Daytona
from daytona import Daytona
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_daytona import DaytonaSandbox

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
                    "content": "Create a small Python package and run pytest",
                }
            ]
        }
    )
finally:
    sandbox.stop()
```

```python
# LangSmith
from deepagents import create_deep_agent
from deepagents.backends import LangSmithSandbox
from langchain_anthropic import ChatAnthropic
from langsmith.sandbox import SandboxClient

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
                    "content": "Create a small Python package and run pytest",
                }
            ]
        }
    )
finally:
    client.delete_sandbox(ls_sandbox.name)
```

For more information, see [[sandboxes.md]].

## Human-in-the-loop

Some tool operations may be sensitive and require human approval before execution.

You can configure approval for each tool:

```python
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def delete_file(path: str) -> str:
    """Delete a file from the filesystem."""
    return f"Deleted {path}"

@tool
def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    return f"Contents of {path}"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Sent email to {to}"

# Checkpointer is REQUIRED for human-in-the-loop
checkpointer = MemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[delete_file, read_file, send_email],
    interrupt_on={
        "delete_file": True,  # Default: approve, edit, reject
        "read_file": False,   # No interrupts needed
        "send_email": {"allowed_decisions": ["approve", "reject"]},  # No editing
    },
    checkpointer=checkpointer  # Required!
)
```

You can configure interrupts for agents and subagents on tool calls as well as from within tool calls.

For more information, see [[human-in-the-loop.md]].

## Skills

You can use skills to provide your deep agent with new capabilities and expertise.

While tools tend to cover lower-level functionality like native file system actions or planning, skills can contain detailed instructions on how to complete tasks, reference info, and other assets, such as templates.

These files are only loaded by the agent when the agent has determined that the skill is useful for the current prompt. This progressive disclosure reduces the amount of tokens and context the agent has to consider upon startup.

For example skills, see Deep Agent example skills.

To add skills to your deep agent, pass them as an argument to `create_deep_agent`:

### Using StateBackend

```python
from urllib.request import urlopen
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/libs/cli/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

skills_files = {
    "/skills/langgraph-docs/SKILL.md": create_file_data(skill_content)
}

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/"],
    checkpointer=checkpointer,
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is langgraph?",
            }
        ],
        # Seed the default StateBackend's in-state filesystem (virtual paths must start with "/")
        "files": skills_files
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

### Using StoreBackend

```python
from urllib.request import urlopen
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/libs/cli/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

store.put(
    namespace=("filesystem",),
    key="/skills/langgraph-docs/SKILL.md",
    value=create_file_data(skill_content)
)

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=StoreBackend(),
    store=store,
    skills=["/skills/"],
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is langgraph?",
            }
        ],
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

### Using FilesystemBackend

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from deepagents.backends.filesystem import FilesystemBackend

# Checkpointer is REQUIRED for human-in-the-loop
checkpointer = MemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=FilesystemBackend(root_dir="/Users/user/{project}"),
    skills=["/Users/user/{project}/skills/"],
    interrupt_on={
        "write_file": True,  # Default: approve, edit, reject
        "read_file": False,  # No interrupts needed
        "edit_file": True    # Default: approve, edit, reject
    },
    checkpointer=checkpointer,  # Required!
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is langgraph?",
            }
        ],
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

For more information, see [[skills.md]].

## Memory

Use `AGENTS.md` files to provide extra context to your deep agent.

You can pass one or more file paths to the `memory` parameter when creating your deep agent:

- StateBackend
- StoreBackend
- FilesystemBackend

### Using StateBackend

```python
from urllib.request import urlopen
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

with urlopen("https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/examples/text-to-sql-agent/AGENTS.md") as response:
    agents_md = response.read().decode('utf-8')

checkpointer = MemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=[
        "/AGENTS.md"
    ],
    checkpointer=checkpointer,
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Please tell me what's in your memory files.",
            }
        ],
        # Seed the default StateBackend's in-state filesystem (virtual paths must start with "/")
        "files": {"/AGENTS.md": create_file_data(agents_md)},
    },
    config={"configurable": {"thread_id": "123456"}},
)
```

### Using StoreBackend

```python
from urllib.request import urlopen
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

with urlopen("https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/examples/text-to-sql-agent/AGENTS.md") as response:
    agents_md = response.read().decode('utf-8')

# Create a store and add the file to it
store = InMemoryStore()
file_data = create_file_data(agents_md)

store.put(
    namespace=("filesystem",),
    key="/AGENTS.md",
    value=file_data
)

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=StoreBackend(),
    store=store,
    memory=[
        "/AGENTS.md"
    ]
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Please tell me what's in your memory files.",
            }
        ],
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

### Using FilesystemBackend

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

# Checkpointer is REQUIRED for human-in-the-loop
checkpointer = MemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=FilesystemBackend(root_dir="/Users/user/{project}"),
    memory=[
        "./AGENTS.md"
    ],
    interrupt_on={
        "write_file": True,  # Default: approve, edit, reject
        "read_file": False,  # No interrupts needed
        "edit_file": True    # Default: approve, edit, reject
    },
    checkpointer=checkpointer,  # Required!
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Please tell me what's in your memory files.",
            }
        ],
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

For more information, see [[memory.md]].

## Structured output

Deep Agents support structured output.

You can set a desired structured output schema by passing it as the `response_format` argument to the call to `create_deep_agent()`.

When the model generates structured data, it's captured, validated, and returned in the 'structured_response' key of the deep agent's state.

```python
import os
from typing import Literal
from pydantic import BaseModel, Field
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

class WeatherReport(BaseModel):
    """A structured weather report with current conditions and forecast."""
    location: str = Field(description="The location for this weather report")
    temperature: float = Field(description="Current temperature in Celsius")
    condition: str = Field(description="Current weather condition (e.g., sunny, cloudy, rainy)")
    humidity: int = Field(description="Humidity percentage")
    wind_speed: float = Field(description="Wind speed in km/h")
    forecast: str = Field(description="Brief forecast for the next 24 hours")

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    response_format=WeatherReport,
    tools=[internet_search]
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "What's the weather like in San Francisco?"
    }]
})

print(result["structured_response"])
# Output: location='San Francisco, California' temperature=18.3 condition='Sunny' humidity=48 wind_speed=7.6 forecast='Pleasant sunny conditions expected to continue with temperatures around 64°F (18°C) during the day, dropping to around 52°F (11°C) at night. Clear skies with minimal precipitation expected.'
```

For more information and examples, see response format documentation.
