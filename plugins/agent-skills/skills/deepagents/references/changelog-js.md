# Changelog (JavaScript) - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/changelog-js.md

# Changelog

Log of updates and improvements to our JavaScript/TypeScript packages

__Subscribe__: Our changelog includes an RSS feed that can integrate with Slack, email, Discord bots like Readybot or RSS Feeds to Discord Bot, and other subscription tools.

Mar 24, 2026 · deepagents

## `deepagents` v1.9.0-alpha.0

Alpha release of `deepagents` v1.9.0.

- __Async subagents__: Deep Agents can launch non-blocking background tasks, so users can continue interacting with the agent while subagents work concurrently. Requires LangSmith Deployment for sub-agents.
- __Backend protocol v2__: We’ve introduced a new v2 backend protocol (`BackendProtocolV2`) with backward-compatible changes to the Deep Agents backend interface. Key changes:
  - __Structured result types__: All methods now return structured `Result` objects (e.g., `ReadResult`, `LsResult`, `GrepResult`, `GlobResult`) with consistent error handling via an `error` field, instead of returning raw values or throwing exceptions.
  - __Multi-modal file support__: `read()` returns a `ReadResult` with a `.content` field instead of a plain string. For binary files (images, PDFs, audio, video), the full raw `Uint8Array` content is returned via `readRaw()`, enabling agents to work with multi-modal files natively.
  - __Simplified method names__: `lsInfo` -> `ls`, `grepRaw` -> `grep`, `globInfo` -> `glob`.
  - __Backward compatible__: Existing v1 backends can be adapted to the v2 interface using `adaptBackendProtocol`. The v1 interfaces (`BackendProtocolV1`, `SandboxBackendProtocolV1`) are deprecated but retained for compatibility.

Jan 14, 2026 · langgraph

## v1.1.0

### `@langchain/langgraph`

Introducing __StateSchema__ - a cleaner, library-agnostic way to define graph state that works with any Standard Schema-compliant validation library.

### Standard JSON Schema support

LangGraph now supports Standard JSON Schema, an open specification implemented by Zod 4, Valibot, ArkType, and other schema libraries. This means you can use your preferred validation library without lock-in:

```
import { z } from "zod"; // or valibot, arktype, etc.
import { StateSchema, ReducedValue, MessagesValue } from "@langchain/langgraph";

const AgentState = new StateSchema({
  messages: MessagesValue,
  currentStep: z.string(),
  count: z.number().default(0),
  history: new ReducedValue(
    z.array(z.string()).default(() => []),
    {
      inputSchema: z.string(),
      reducer: (current, next) => [...current, next],
    }
  ),
});

// Type-safe state and update types
type State = typeof AgentState.State;
type Update = typeof AgentState.Update;

const graph = new StateGraph(AgentState)
  .addNode("agent", (state) => ({ count: state.count + 1 }))
  .addEdge(START, "agent")
  .addEdge("agent", END)
  .compile();
```

### New state value primitives

- __ReducedValue__: Define fields with custom reducers for accumulating values. Supports separate input and output schemas for type-safe reducer inputs.
- __UntrackedValue__: Define transient state that exists during execution but is never checkpointed - useful for database connections, caches, or runtime-only configuration.
- __MessagesValue__: A prebuilt `ReducedValue` for chat messages with the standard messages reducer.

### Type helper exports

New exported type utilities for typing functions outside the graph builder:

- `GraphNode<Schema, Nodes?, Config?>` - Type node functions with full inference
- `ConditionalEdgeRouter<Schema, Nodes?>` - Type conditional edge routers

```
// Type standalone node functions
const myNode: GraphNode<typeof AgentState> = (state, config) => {
  return { count: state.count + 1 };
};

// Use schema type helpers directly
const processState = (state: typeof AgentState.State) => {
  console.log(state.count);
};
```

The existing `Annotation` and zod-based API continues to work unchanged - `StateSchema` is an additional option for those who prefer schema-first definitions.

## Learn more about StateSchema

See the full documentation for defining graph state with StateSchema, ReducedValue, and UntrackedValue.

## Learn about type utilities

Use GraphNode and ConditionalEdgeRouter to type functions outside the graph builder.

Dec 12, 2025 · langchain, @langchain/openai, @langchain/anthropic, @langchain/ollama, @langchain/community, @langchain/xai, @langchain/tavily, @langchain/mongodb, @langchain/mcp-adapters, @langchain/google-common, @langchain/core

## v1.2.0

### `langchain`

- Structured output: Added ability to manually set `strict` mode when using `providerStrategy` for structured output.

### `@langchain/openai`

- __New provider built-in tools:__ Support for file search, web search, code interpreter, image generation, computer use, shell, and MCP connector tools executed server-side by the provider. See Server-side tool use and the OpenAI chat integration.
- __Content moderation:__ New `moderateContent` option on `ChatOpenAI` for detecting and handling unsafe content.
- Prefer responses API for GPT-5.2 Pro model.

## v1.3.0

### `@langchain/anthropic`

- __New provider built-in tools:__ Support for text editor, web fetch, computer use, tool search, and MCP toolset tools executed server-side by the provider. See Server-side tool use and the Anthropic chat integration.
- Exposed `ChatAnthropicInput` type for improved type safety.

## v1.1.0

### `@langchain/ollama`

- __Native structured outputs:__ Added support for native structured output via `withStructuredOutput`.
- Support for custom `baseUrl` configuration.

## v1.0.0

### `@langchain/community`

- Jira document loader updated to use v3 API.
- LanceDB: Added `similaritySearch()` and `similaritySearchWithScore()` support.
- Elasticsearch hybrid search support.
- New `GoogleCalendarDeleteTool`.
- Various bug fixes for LlamaCppEmbeddings, PrismaVectorStore, IBM WatsonX, and security improvements.

### Other packages

- __@langchain/xai:__ Native Live Search support.
- __@langchain/tavily:__ Added Tavily’s research endpoint.
- __@langchain/mongodb:__ New MongoDB LLM cache.
- __@langchain/mcp-adapters:__ Added `onConnectionError` option.
- __@langchain/google-common:__ `jsonSchema` method support in `withStructuredOutput`.
- __@langchain/core:__ Security fixes, better subgraph nesting in Mermaid graphs, UUID7 for run IDs.

Nov 25, 2025 · langchain

## v1.1.0

- Model profiles: Chat models now expose supported features and capabilities through a `.profile` getter. These data are derived from models.dev, an open source project providing model capability data.
- Model retry middleware: New middleware for automatically retrying failed model calls with configurable exponential backoff, improving agent reliability.
- Content moderation middleware: OpenAI content moderation middleware for detecting and handling unsafe content in agent interactions. Supports checking user input, model output, and tool results.
- Summarization middleware: Updated to support flexible trigger points using model profiles for context-aware summarization.
- Structured output: `ProviderStrategy` support (native structured output) can now be inferred from model profiles.
- `SystemMessage` for `createAgent`: Support for passing `SystemMessage` instances directly to `createAgent`’s `systemPrompt` parameter and a new `concat` method for extending system messages. Enables advanced features like cache control and structured content blocks.
- Dynamic system prompt middleware: Return values from `dynamicSystemPromptMiddleware` are now purely additive. When returning a `SystemMessage` or `string`, they are merged with existing system messages rather than replacing them, making it easier to compose multiple middleware that modify the prompt.
- __Compatibility improvements:__ Fixed error handling for Zod v4 validation errors in structured output and tool schemas, ensuring detailed error messages are properly displayed.

Oct 20, 2025 · langchain, langgraph

## v1.0.0

### `langchain`

- Release notes
- Migration guide

### `langgraph`

- Release notes
- Migration guide

If you encounter any issues or have feedback, please open an issue so we can improve. To view v0.x documentation, go to the archived content.

---

[Edit this page on GitHub](https://github.com/langchain-ai/docs) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
