# Skills - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/skills

## Overview

You can use skills to provide your deep agent with new capabilities and expertise. While tools tend to cover lower level functionality like native file system actions or planning, skills can contain detailed instructions on how to complete tasks, reference info, and other assets.

## How it works

These files are **only loaded by agent when the agent has determined that skill is useful for the current prompt**. This progressive disclosure reduces token usage and context clutter.

Each skill should be a directory containing a `SKILL.md` file with instructions and metadata. The structure follows:

```
/skills/my-skill/
├── SKILL.md        (frontmatter + content)
└── ...
    (optional assets like templates, reference docs, etc.)
```

When a skill is loaded, the agent:

1. Reads the `SKILL.md` frontmatter at startup for metadata
2. Loads the full skill content only when the agent determines it's relevant
3. Makes the skill's tools available (if defined in subdirectory)
4. Executes the skill content (if it contains scripts or instructions)

## Creating a skill

### Frontmatter

The `SKILL.md` file should include YAML frontmatter with metadata:

```yaml
---
name: My Skill
description: A specialized skill for XYZ
trigger_words: ["word1", "word2"]
```

**Required fields:**
- `name`: A short, descriptive name for the skill
- `description`: Clear description of what the skill does

**Optional fields:**
- `version`: Skill version for tracking updates
- `author`: Author attribution
- `trigger_words`: Array of keywords that should trigger this skill
- `examples`: Example usage scenarios
- `dependencies`: Other skills this skill requires
- `category`: Category for organization

### Content structure

After the frontmatter, include your skill instructions:

```markdown
# [Description of what this skill does]

## Background

[Context about why this skill exists]

## Instructions

[Step-by-step instructions for the agent]

## Resources

[Links to reference materials, templates, or documentation]

## Examples

[Code snippets or usage examples]
```

## Agent integration

When you pass skills paths to `create_deep_agent(skills=[...])`, the agent can use those skills as needed.

### Skill tools

Skills can include their own tools that the agent can access. These tools are available when the skill is loaded.

```python
from langchain.tools import tool
from langchain.tools import ToolRuntime

@tool
def my_skill_tool(query: str, runtime: ToolRuntime) -> str:
    """Custom tool from my skill."""
    # Access skill-specific configuration if provided
    skill_config = runtime.store.get("my_skill_config", {})
    return execute_my_skill(query, **skill_config)

def execute_my_skill(query: str, **config: dict) -> str:
    """Execute my skill logic."""
    return f"Executed: {query} with config {config}"
```

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/my-skill/"],  # Agent can now use my_skill_tool
)
```

### Skill loading behavior

1. **Progressive**: Only loaded when relevant
2. **Frontmatter first**: Agent reads all frontmatters at startup to decide which skills might be useful
3. **Content on-demand**: Full content only loaded when skill is invoked
4. **Tool availability**: Skills expose their tools only when loaded
5. **No inheritance**: Custom subagents do NOT inherit parent's skills (only general-purpose subagent does)

## Best practices

### One skill per capability

Create focused skills that address a single use case rather than trying to do everything:

✅ **Good**: `/skills/research/`, `/skills/code-analysis/`
❌ **Bad**: `/skills/everything/` (too broad)

### Keep skills focused

Write concise, actionable instructions. Avoid lengthy reference materials in the main `SKILL.md`.

**Frontmatter example:**
```yaml
---
name: Web Research
description: Conducts web research using Tavily
trigger_words: ["research", "search", "web", "find", "look up"]
examples:
  - "Find information about [topic]"
```

**Content example:**
```markdown
## How to use this skill

This skill provides web research capabilities using Tavily.

### Available Tools

When this skill is loaded, you have access to the following tools:

| Tool | Description |
| --- | --- |
| `search_web` | Search for information on the web. Takes a query and optional parameters for max results and topic. |
| `summarize_results` | Summarize search results into a concise overview. Useful when you need to process multiple sources. |

### Usage Example

```python
agent.invoke(
    {"messages": [{"role": "user", "content": "Research recent developments in quantum computing"}]}
)
```

The agent will automatically load this skill and use the web research tools when appropriate.

## Managing skills

### Directory structure

Organize your skills in a logical directory structure:

```
/skills/
├── web-search/          # Web research skill
│   └── SKILL.md
├── code-analysis/          # Code analysis skill
│   └── SKILL.md
├── general-assistant/      # General purpose assistant
│   └── SKILL.md
└── utils/                  # Shared utility functions
    └── shared_utils.py
```

### Shared utilities

For common functionality across multiple skills, create a shared utilities module:

```python
# /skills/utils/shared_utils.py

def format_response(data: dict) -> str:
    """Format a response consistently across all skills."""
    return f"Processed: {data['type']} - {data.get('summary', 'N/A')}"

def validate_input(input_data: str) -> bool:
    """Validate common input across skills."""
    return len(input_data.strip()) > 0
```

### Skill versioning

Use the `version` field in frontmatter to track updates:

```yaml
---
version: 1.0.0
author: Example Corp
trigger_words: ["analyze", "data"]
```

When you update a skill, increment the version and document what changed.

## Progressive disclosure

Skills use progressive disclosure to reduce token usage:

1. **Startup**: All frontmatter is read (low token cost)
2. **Filter**: Agent determines which skills are relevant (no token cost)
3. **Load**: Only full content when skill is actually used (saves tokens)
4. **Unload**: Content is removed from working memory after use

This ensures the agent only loads what it needs.

## Skills vs Memory

| Aspect | Skills | Memory |
| --- | --- | --- |
| Loading | On-demand | Always loaded |
| Updates | Agent can update | Agent typically doesn't modify |
| Content | Instructions | Can include workflows | Static conventions |
| Purpose | Specialized workflows | Persistent context |
| Use case | Task-specific | General context |

Use skills for workflows with multiple steps and reference docs. Use memory for conventions and persistent context.

## Troubleshooting

### Skill not loading

**Problem**: Agent doesn't see the skill or its tools.

**Solutions**:

1. Check file path is correct (use absolute path or relative to skills root)
2. Verify `SKILL.md` exists with proper frontmatter
3. Check skills directory is included in `create_deep_agent(skills=[...])`
4. Test the skill with a simple query first

### Tool not available

**Problem**: Skill tools are not accessible.

**Solutions**:

1. Verify tool functions are properly decorated with `@tool`
2. Check tool imports are included in the `SKILL.md` subdirectory
3. Check agent was created with proper skills configuration
4. Add debug logging to verify tool availability

## Advanced features

### Skill chaining

Skills can reference other skills as dependencies using the `dependencies` field in frontmatter:

```yaml
---
name: Advanced Analysis
description: Performs in-depth data analysis
dependencies:
  - /skills/code-analysis/
  - /skills/web-search/
examples:
  - "Analyze sales data and generate insights"
  - "Research market trends and provide recommendations"
```

When loaded, this skill can use tools from both dependencies.

### Dynamic skill loading

Skills can be loaded from external sources or generated dynamically:

```python
from deepagents import create_deep_agent

# Load skills from multiple sources
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=[
        "/skills/local/",      # Local files
        "https://skills.example.com/api",  # Remote skill registry
    ],
    system_prompt="You have access to skills from multiple sources.",
)
```
