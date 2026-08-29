# Memory - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/memory

## Overview

Use `AGENTS.md` files to provide extra context to your deep agent across conversations. These files often contain general coding style, preferences, conventions, and guidelines that help the agent understand how to work with your codebase and follow your preferences.

## How it works

Memory files provide persistent context that is **always loaded** into the system prompt. Unlike skills, which use progressive disclosure (only loaded when relevant), memory files are injected on every agent startup.

You can pass one or more file paths to the `memory` parameter when creating your deep agent. Files are stored in the agent's backend (StateBackend, StoreBackend, or FilesystemBackend) and the agent can update them based on your interactions, feedback, and identified patterns.

**Key differences from skills:**

| Aspect | Memory | Skills |
| --- | --- | --- |
| Loading | Always loaded | Progressive (on-demand) |
| Storage | In agent's backend | Separate skill directories |
| Purpose | Persistent context | Specialized workflows |
| Update | Agent can update | Agent typically doesn't modify skills |

## When to use memory

Use memory when you have:

- **Project conventions** - Coding style, naming conventions, architectural patterns
- **User preferences** - Response format preferences (concise vs. detailed), formatting guidelines
- **Critical guidelines** - Security policies, deployment procedures, error handling patterns
- **Domain knowledge** - Industry-specific information, company history, product details
- **Session continuity** - Preferences that should persist across different conversations

Do NOT use memory for:

- One-off information that could be provided in the current prompt
- Temporary data that changes frequently
- Large reference documents that bloat context (use skills with progressive disclosure instead)

## Backends

Memory files are stored using the same backend that your agent uses for filesystem operations.

### StateBackend (ephemeral)

Files are stored in LangGraph agent state. Memory persists across multiple agent turns on the same thread via checkpoints. When the thread ends, memory is lost.

```python
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

checkpointer = MemorySaver()
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/project/AGENTS.md"],
    checkpointer=checkpointer,
)

# Seed memory file for agent to read
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's in your memory?"}]},
    config={
        "configurable": {"thread_id": "12345"},
        "files": {"/AGENTS.md": create_file_data(agents_md)},
    },
)
```

### StoreBackend (persistent)

Files are stored in a LangGraph Store, providing cross-thread persistence. Memory persists across different conversations and sessions.

```python
from deepagents.backends.utils import create_file_data
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore
from langchain.messages import HumanMessage

# Create a store and add a file to it
store = InMemoryStore()
agents_md = "# My Agent Guidelines\n\n..."
file_data = create_file_data(agents_md)
store.put(
    namespace=("filesystem",),
    key="/AGENTS.md",
    value=file_data,
)

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=StoreBackend(),
    store=store,
    memory=["/AGENTS.md"],
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's in your memory?"}]},
    config={
        "configurable": {"thread_id": "12345"},
    },
)
```

### FilesystemBackend (local disk)

Files are stored as regular files in your local filesystem. The agent can read and update them like any other file.

```python
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

checkpointer = MemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=FilesystemBackend(root_dir="/Users/user/{project}"),
    memory=["/Users/user/{project}/AGENTS.md"],
    checkpointer=checkpointer,
)

# Agent can update memory file
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Update your guidelines"}],
    "config": {"configurable": {"thread_id": "12345"}},
    )
```

**Important**: When using FilesystemBackend with memory, the memory file path must be an absolute path to the filesystem root or relative to the agent's root_dir.

## Storage location

- **StateBackend**: Stored in LangGraph state in thread. Lost when thread ends.
- **StoreBackend**: Stored in LangGraph Store. Persistent across threads/sessions. Accessible from any agent using that store.
- **FilesystemBackend**: Stored as regular files in specified `root_dir`. Agent can read/write them directly.

## Best practices

### Keep memory focused

Store only essential information that applies to every conversation:

✅ **Good**:
```markdown
# Coding Standards

- Use 2 spaces for indentation
- Follow PEP 8 style for naming
- Use type hints for functions
- Add docstrings to all functions
- Prefer composition over inheritance

# Project Structure
src/
├── components/
│   ├── Button.tsx
│   └── InputField.tsx
└── utils/
    └── helpers.py

# API Response Format
- Use snake_case for JSON keys
- Include `error_code` field in error responses
```

❌ **Bad**:
```markdown
# Please use the following conventions...
- Some guidelines here
- More guidelines there
- And even more here
```

### Update memory dynamically

The agent can update memory files based on user interactions and feedback:

```python
# Agent detects patterns and updates memory
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/AGENTS.md"],
    system_prompt="""Maintain AGENTS.md with coding standards.
    When users provide new conventions, update the file.
    When users change preferences, document them in memory.
    """,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Add TypeScript to your guidelines"}]},
    # Memory will be updated
)
```

### Use separate files for different domains

Organize memory by domain or purpose:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=[
        "/project/coding-standards.md",      # Coding conventions
        "/project/user-preferences.md",   # User preferences
        "/product/business-logic.md",   # Domain knowledge
        "/company/deployment-guide.md",  # Operational procedures
    ],
)
```

### Memory vs Skills

| Aspect | Memory | Skills |
| --- | --- | --- |
| Loading | Always | On-demand |
| Storage | Agent's backend | Skill directories |
| Update | Agent can update | Agent typically doesn't modify skills |
| Use case | Context, preferences | Workflows |
| File format | `.md` | Has frontmatter |

**When to choose:**

- Use **memory** for: project conventions, user preferences, persistent guidelines
- Use **skills** for: specialized workflows, reference documentation, templates

**Example**:
```python
memory = [
    # Persistent conventions
    "/project/conventions.md",

    # Specialized capability
    "/skills/research-guide.md",  # Loaded only when needed
]
```

## Common patterns

### Startup memory

Provide initial context when the agent is created:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/project/AGENTS.md", "/project/standards.md"],
    system_prompt="""You are a coding assistant for this project.

    Project conventions:
    - Language: TypeScript
    - Framework: React with Next.js
    - API: FastAPI

    Follow the guidelines in /project/conventions.md.
    Standards from /project/standards.md apply to all code.
    """,
)
```

### User profile memory

Store user-specific information that improves personalization:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/users/user-{id}/preferences.md"],
    system_prompt="""You are a personalized assistant.

    Remember each user's preferences:
    - Response style: concise
    - Code language preference: Python
    - Documentation format: Markdown

    Check /users/{user_id}/preferences.md before making decisions.
    """,
)
```

### Knowledge base memory

Store domain knowledge for complex queries:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/knowledgebase/product-info.md", "/knowledgebase/api-reference.md"],
    system_prompt="""You have access to product knowledge and API documentation.

    Use /knowledgebase/ files when answering technical questions.
    Cross-reference information between product info and API docs.
    """,
)
```

## Troubleshooting

### Memory file not being read

**Problem**: Agent doesn't see expected memory content.

**Solutions**:

1. **Check file path**: Ensure memory file path is correct (absolute for StoreBackend, relative to agent's root_dir for FilesystemBackend)
2. **Verify file exists**: The file should exist in the configured backend
3. **Check backend**: Verify the agent is using the backend where memory files are stored
4. **Use seeds file**: When creating agent with memory, seed the memory file using `config.files` parameter

```python
from deepagents.backends.utils import create_file_data

# Create memory file content
agents_md_content = "# My Guidelines\n..."

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What are your guidelines?"}]},
    config={
        "configurable": {"thread_id": "12345"},
        "files": {"/AGENTS.md": create_file_data(agents_md_content)},
    },
)
```

### Agent not updating memory

**Problem**: User feedback or identified patterns aren't being reflected in memory.

**Solutions**:

1. **Include update instructions in system prompt**:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/AGENTS.md"],
    system_prompt="""Maintain AGENTS.md actively.

    When users provide new conventions:
    - Update the file
    - Add a new section
    - Document the change date

    When users identify patterns:
    - Document those patterns
    - Extract them as guidelines
    """,
)
```

2. **Use @dynamic_prompt with tools**:

```python
from deepagents.middleware import dynamic_prompt
from langchain.agents.middleware import wrap_tool_call

call_count = [0]

@wrap_tool_call
def update_memory_on_interaction(request, handler):
    """Update memory based on user interaction."""
    global call_count
    call_count[0] += 1

    tool_name = request.name if hasattr(request, "name") else str(request)
    print(f"[Memory Update] Tool call #{call_count[0]}: {tool_name}")

    result = handler(request)

    # Signal that memory should be updated
    return result

@dynamic_prompt
def memory_prompt_generator(request):
    """Generate prompt to update memory."""
    tool_info = f"User called {request.args.get('tool', 'unknown')} at {request.runtime.metadata.get('timestamp', 'N/A')}"

    return (
        f"The user has made an interaction: {tool_info}.\n"
        f"Please check if this affects AGENTS.md and update it accordingly.\n"
        f"If the change adds new conventions, add them to the file.\n"
        f"If the change fixes an issue, document it.\n"
        f"If the change is about preferences, update /users/{{user_id}}/preferences.md.\n"
    )

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/AGENTS.md"],
    middleware=[update_memory_on_interaction],
)
```

## Advanced usage

### Combining memory with long-term memory

Use the `CompositeBackend` to have both ephemeral state and persistent `/memories/` storage:

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={"/memories/": StoreBackend(runtime)},
    )

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=make_backend,
    store=InMemoryStore(),
    system_prompt="""You have two storage layers:

1. Ephemeral workspace (/workspace/) - cleared each session
2. Long-term memories (/memories/) - persists across sessions

Use /workspace/ for temporary work.
Use /memories/ for anything that should persist, like user preferences, project knowledge, or learning progress.
""",
)
```

### Memory with skills

Skills can reference memory files to provide context for their workflows:

```python
# /skills/analysis/SKILL.md
"""Analysis Skill

This skill requires access to project memory.

Dependencies:
- /project/conventions.md - coding standards
- /project/business-logic.md - domain rules
"""

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/project/conventions.md", "/project/business-logic.md"],
    skills=["/skills/analysis/"],
)
```
