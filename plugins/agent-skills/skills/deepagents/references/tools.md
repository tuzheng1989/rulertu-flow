# Tools - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/tools.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Tools

> Connect Deep Agents to custom functions, APIs, databases, and any MCP server

Deep Agents can call any tool you define, any [LangChain tool](https://python.langchain.com/docs/concepts/tools/), and tools from any [MCP server](#mcp-tools).
Pass them to `create_deep_agent` via the `tools=` parameter alongside the [built-in harness tools](/oss/python/deepagents/overview#execution-environment) for file management and subagent spawning.

<CodeGroup>
  ```python Google theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="google_genai:gemini-3.6-flash",
      tools=[search, fetch_url, run_query],
  )
  ```

  ```python OpenAI theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="openai:gpt-5.5",
      tools=[search, fetch_url, run_query],
  )
  ```

  ```python Anthropic theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="anthropic:claude-sonnet-4-6",
      tools=[search, fetch_url, run_query],
  )
  ```

  ```python OpenRouter theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="openrouter:z-ai/glm-5.2",
      tools=[search, fetch_url, run_query],
  )
  ```

  ```python Fireworks theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="fireworks:accounts/fireworks/models/glm-5p2",
      tools=[search, fetch_url, run_query],
  )
  ```

  ```python Baseten theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="baseten:zai-org/GLM-5.2",
      tools=[search, fetch_url, run_query],
  )
  ```

  ```python Ollama theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from deepagents import create_deep_agent


  agent = create_deep_agent(
      model="ollama:north-mini-code-1.0",
      tools=[search, fetch_url, run_query],
  )
  ```
</CodeGroup>

## Custom tools

Pass any callable, such as plain functions, LangChain `@tool`-decorated functions, or tool dicts—directly to `tools=`.
Deep Agents infers the tool schema from the function signature and docstring, so you don't need to define a separate schema in most cases.

<CodeGroup>
  ```python Google theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="google_genai:gemini-3.6-flash",
      tools=[internet_search],
  )
  ```

  ```python OpenAI theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="openai:gpt-5.5",
      tools=[internet_search],
  )
  ```

  ```python Anthropic theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="anthropic:claude-sonnet-4-6",
      tools=[internet_search],
  )
  ```

  ```python OpenRouter theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="openrouter:z-ai/glm-5.2",
      tools=[internet_search],
  )
  ```

  ```python Fireworks theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="fireworks:accounts/fireworks/models/glm-5p2",
      tools=[internet_search],
  )
  ```

  ```python Baseten theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="baseten:zai-org/GLM-5.2",
      tools=[internet_search],
  )
  ```

  ```python Ollama theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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
      model="ollama:north-mini-code-1.0",
      tools=[internet_search],
  )
  ```
</CodeGroup>

For full details on defining and using LangChain tools (tool dicts, `StructuredTool`, return types, error handling, and more), see [Tools](/oss/python/langchain/tools).

## MCP tools

<Note>
  Deep Agents fully support [Model Context Protocol (MCP)](/oss/python/langchain/mcp), the open standard for connecting agents to external services. Load tools from any MCP server and pass them directly to `create_deep_agent`.
</Note>

MCP is an open protocol that lets agents connect to a growing ecosystem of servers—databases, APIs, file systems, browsers, and more—through a standard interface. Instead of writing custom integration code for each service, you point Deep Agents at an MCP server and it gets all the tools that server exposes.

Install `langchain-mcp-adapters` to connect to MCP servers:

<CodeGroup>
  ```bash pip theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  pip install langchain-mcp-adapters
  ```

  ```bash uv theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  uv add langchain-mcp-adapters
  ```
</CodeGroup>

<CodeGroup>
  ```python Google theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="google_genai:gemini-3.6-flash",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```

  ```python OpenAI theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="openai:gpt-5.5",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```

  ```python Anthropic theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="anthropic:claude-sonnet-4-6",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```

  ```python OpenRouter theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="openrouter:z-ai/glm-5.2",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```

  ```python Fireworks theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="fireworks:accounts/fireworks/models/glm-5p2",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```

  ```python Baseten theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="baseten:zai-org/GLM-5.2",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```

  ```python Ollama theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient
  from deepagents import create_deep_agent


  async def main():
      client = MultiServerMCPClient(
          {
              "my_server": {
                  "transport": "http",
                  "url": "http://localhost:8000/mcp",
              }
          }
      )
      tools = await client.get_tools()

      agent = create_deep_agent(
          model="ollama:north-mini-code-1.0",
          tools=tools,
      )

      result = await agent.ainvoke(
          {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
          config={"configurable": {"thread_id": "1"}},
      )


  asyncio.run(main())
  ```
</CodeGroup>

For detailed configuration options—including stdio servers, OAuth authentication, tool filtering, and stateful sessions—see the full [MCP guide](/oss/python/langchain/mcp).

## Built-in harness tools

In addition to the tools you provide, every Deep Agent comes with a built-in set of tools from the harness:

| Tool         | Description                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| `ls`         | List files in a directory.                                                                                |
| `read_file`  | Read file contents (with pagination and multimodal support).                                              |
| `write_file` | Create a new file, or overwrite an existing one.                                                          |
| `edit_file`  | Perform exact string replacements in files.                                                               |
| `delete`     | Delete a file, or a directory and its contents recursively. The `delete` tool requires `deepagents>=0.7`. |
| `glob`       | Find files matching a glob pattern.                                                                       |
| `grep`       | Search file contents.                                                                                     |
| `execute`    | Run shell commands (sandbox backends only).                                                               |
| `task`       | Spawn a subagent to handle a delegated task.                                                              |

To add structured task planning with `write_todos`, opt in with [`TodoListMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/todo/TodoListMiddleware). See [Task planning](/oss/python/deepagents/overview#task-planning).

For a full breakdown of what each built-in tool does, see [Harness overview](/oss/python/deepagents/overview#execution-environment).

## Multimodal tool outputs

Custom tools can return plain text or [standard content blocks](/oss/python/langchain/messages#standard-content-blocks) (text, images, audio, video, and files) when the selected model supports multimodal tool results. The built-in `read_file` tool also returns multimodal blocks for supported non-text file types.

Return a string for text-only results, or an ordered list of content blocks for text plus media or interleaved multimodal output. See [Multimodal](/oss/python/deepagents/multimodal) and [Tool return values](/oss/python/langchain/tools#return-multimodal-content) for examples and context-compression considerations.

***

<div className="source-links">
  <Callout icon="terminal-2">
    [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
  </Callout>

  <Callout icon="edit">
    [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/deepagents/tools.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
  </Callout>
</div>
