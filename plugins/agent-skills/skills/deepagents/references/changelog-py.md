# Changelog (Python) - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/changelog-py.md

# Changelog

Log of updates and improvements to our Python packages

__Subscribe__: Our changelog includes an RSS feed that can integrate with Slack, email, Discord bots like Readybot or RSS Feeds to Discord Bot, and other subscription tools.

Jul 24, 2026 · deepagents

## `deepagents` v0.7.0

A leaner, more configurable harness by default. On a default-agent turn, input tokens drop __65%__ (5,395 → 1,895), validated against our revamped evaluation suite with no quality regression.

### Optimizations

- __Lean prompts by default__: The authored base prompt starts empty and tool-usage prose that duplicated tool schemas has been trimmed. Isolated to the default agent’s tool schemas, total description tokens drop __43%__ (4,005 → 2,302); combined with the empty base prompt and opt-in todos, a default-agent turn’s input tokens drop __65%__ (5,395 → 1,895). Tool behavior is unchanged. (#4859, #4979, #5009)

### Features

- __Override a default middleware instance__: A `middleware=` (or subagent `middleware`) instance whose `.name` matches a built-in now replaces that default in place, rather than erroring on a duplicate. For example, pass your own `SummarizationMiddleware(...)` to change the token trigger or summary model without disabling the built-in default. (#4251)
- __Filesystem tools__: New `delete` tool removes a file or recursively removes a directory (#3659, #3851); `write_file` now overwrites an existing file instead of erroring (#4109); `FilesystemMiddleware` accepts a tool allowlist to expose only selected built-in tools (#4325, #4698); and reads and searches are tuned for open models — paginated `read_file` reports total and remaining lines plus the next `offset` (#4540), `grep`/`glob` return partial results with a `truncated` flag instead of hanging on large trees (#4063), and `grep` gains a 1,000-match cap with streamed output and optional context lines (#4570, #4706).
- __More prompt-caching support__: Bedrock prompt caching via the `deepagents[aws]` extra (#4108), and automatic Fireworks prompt-cache session affinity (#4598).
- __NVIDIA support__: A built-in Nemotron 3 Ultra harness profile plus NIM app-origin attribution. (#4192, #4455)

### Breaking changes

- __Planning todos are opt-in__: `create_deep_agent` no longer includes `TodoListMiddleware` by default, so the `write_todos` tool, `todos` state channel, and todo-planning prompt are absent unless restored with `middleware=[TodoListMiddleware()]`. (The OpenAI Codex harness profile still opts in automatically.) (#4929)
- __Backend compatibility shims removed__: Pass concrete `BackendProtocol` instances instead of factories, configure `StoreBackend` with an explicit `namespace`, and use the current `ls` / `glob` / `grep` / `ReadResult` APIs. Removed symbols include `BackendFactory`, `BACKEND_TYPES`, `FileFormat`, and `Unset`. New files store string `FileData.content`; older `list[str]` content stays readable and converts on next write. (#4541)
- __Output format changes__: Empty `ls` / `glob` output is now `No files found` instead of `[]`, and `read_file` no longer renders a fixed-width `cat -n`-style gutter — update any parsers of raw tool output. (#4561)

Copy the following prompt into your AI coding assistant to migrate a codebase for these breaking changes:

> Migrate a deepagents codebase from v0.6.x to v0.7.

May 12, 2026 · deepagents

## `deepagents` v0.6.0

- __`CodeInterpreterMiddleware`__: (experimental) `deepagents` now supports code execution and programmatic tool calling through a scoped QuickJS runtime.
- Supports `version="v3"` in `stream_events` / `astream_events`. Refer to the event streaming guide for details.
- __`DeltaChannel` (beta)__ (blog): Deep Agents now uses `DeltaChannel` for message history and agent files. Rather than re-serializing the full accumulated value into every checkpoint, only the incremental delta written at each step is stored — keeping checkpoint sizes small as threads grow long.
- __Harness profiles__: Register per-provider or per-model configuration bundles (`HarnessProfile`) that `create_deep_agent` applies automatically when a model is selected — system-prompt tweaks, tool overrides, middleware changes, and subagent defaults — without modifying the call site.
- __`ContextHubBackend`__ (blog): A new filesystem backend backed by LangSmith Hub. Agent files — skills, memories, and other persisted context — are stored as Hub commits, giving you version history on every write and LangSmith-native durability without provisioning a separate LangGraph store.

May 12, 2026 · langchain

## `langchain` v1.3.0

This release adds support for `version="v3"` in `stream_events` / `astream_events` for `langchain` agents. Refer to the event streaming guide for details.

May 12, 2026 · langgraph

## `langgraph` v1.2.0

This release adds finer-grained control over node execution (timeouts, error recovery, and graceful shutdown), a new channel type that cuts checkpoint overhead for long-running threads, and a new content-block-centric streaming API (v3) with typed, per-channel projections.

- __`DeltaChannel` (beta)__: A new channel type that stores only the incremental delta at each step rather than re-serializing the full accumulated value. Most useful for channels that grow large over time, for example a message list in a long-running thread. Use `snapshot_frequency=K` to write a full snapshot every K steps and bound read latency.
- __Per-node timeouts__: Pass `timeout=` to `add_node` to cap how long a single attempt may run. Set a hard wall-clock limit (`run_timeout`), an idle limit that resets on progress (`idle_timeout`), or both via `TimeoutPolicy`. When the limit fires, LangGraph raises `NodeTimeoutError`, clears writes from that attempt, and hands off to the retry policy. Async nodes only.
- __Node-level error handlers__: Pass `error_handler=` to `add_node` to run a recovery function after all retries are exhausted. The handler receives a typed `NodeError` and can return a `Command` to update state and route to a different node, useful for Saga/compensation patterns.
- __Graceful shutdown__: Stop an in-flight run cooperatively after the current superstep completes, and save a resumable checkpoint. Create a `RunControl` and call `request_drain()` from any thread; the run raises `GraphDrained` and can be resumed later with the same config.
- __New event streaming API (beta)__: Pass `version="v3"` to `stream_events()` / `astream_events()` for a content-block-centric protocol with typed, per-channel projections (`run.values`, `run.messages`, `run.lifecycle`, `run.subgraphs`) plus opt-in transformers for updates, custom events, checkpoints, tasks, and debug. `run.messages` yields one `ChatModelStream` per LLM call with typed sub-projections for text, reasoning, tool calls, and usage. `version="v1"` and `version="v2"` are unchanged.

Timeouts and error handlers are Python-only; retry policies continue to work in both Python and TypeScript.

Apr 7, 2026 · deepagents

## `deepagents` v0.5.0

- __Async subagents__: Deep Agents can launch non-blocking background tasks, so users can continue interacting with the agent while subagents work concurrently. Requires LangSmith Deployment for sub-agents.
- __Multi-modal support__: The `read_file` tool now supports PDFs, audio, and video files in addition to images.
- __Backend changes__: We’ve made backward-compatible changes to the Deep Agents backend protocol:
  - Updated the file format stored in State and Store backends to support binary files.
  - Improved error propagation from backends to tools.
  - You can now instantiate `StateBackend()` and `StoreBackend()` directly. Specifying with a factory (e.g., `backend=(lambda rt: StateBackend(rt))`) is deprecated.
- __Anthropic prompt caching improvements__: We’ve made some improvements to improve prompt caching performance for Anthropic models.

Mar 10, 2026 · langgraph

## `langgraph` v1.1.0

- __Type-safe streaming (`version="v2"`)__: Pass `version="v2"` to `stream()` / `astream()` for unified `StreamPart` output with `type`, `ns`, and `data` keys on every chunk. Each mode has its own `TypedDict`, all importable from `langgraph.types`. See streaming docs.
- __Type-safe invoke (`version="v2"`)__: Pass `version="v2"` to `invoke()` / `ainvoke()` to get a `GraphOutput` object with `.value` and `.interrupts` attributes. See invoke docs.
- __Pydantic and dataclass coercion__: With `version="v2"`, `invoke()` and `values`-mode stream output are automatically coerced to your declared Pydantic model or dataclass type.
- __Fixed time travel with interrupts and subgraphs__: Replays no longer reuse stale `RESUME` values, and subgraphs correctly restore the checkpoint for the parent’s historical state.
- __Fully backwards compatible__: `version="v2"` is opt-in. `GraphOutput` supports deprecated dict-style access for gradual migration.

Feb 10, 2026 · deepagents

## `deepagents` v0.4.0

- New integration packages for pluggable sandboxes: `langchain-modal`, `langchain-daytona`, and `langchain-runloop`. See sandboxes guide and example data analysis tutorial.
- Changes to conversation history summarization:
  - Summarization now happens in the model node via `wrap_model_call` events. Due to this we retain the full message history in the graph state.
  - More accurate token counting.
  - Summarization will now automatically trigger if a chat model raises a `ContextOverflowError` (defined in `langchain-core`). Currently `langchain-anthropic` and `langchain-openai` support this.
- We now default to the Responses API for model strings prefixed with `"openai:"`.

  Disable data retention with the Responses API

  ```
  from langchain.chat_models import init_chat_model

  agent = create_deep_agent(
      model=init_chat_model(
          "openai:...",
          use_responses_api=True,
          store=False,
          include=["reasoning.encrypted_content"],
      )
  )
  ```

Dec 15, 2025 · langchain, integrations

## `langchain` v1.2.0

- `create_agent`: Simplified support for provider-specific tool parameters and definitions via a new `extras` attribute on tools. Examples:
  - Provider-specific configuration such as Anthropic’s programmatic tool calling and tool search.
  - Built-in tools that are executed client-side, as supported by Anthropic, OpenAI, and other providers.
- Support for strict schema-adherence in agent `response_format` (see `ProviderStrategy` docs).

Dec 8, 2025 · langchain, integrations

## `langchain-google-genai` v4.0.0

We’ve re-written the Google GenAI integration to use Google’s consolidated Generative AI SDK, which provides access to the Gemini API and Vertex AI Platform under the same interface. This includes minimal breaking changes as well as deprecated packages in `langchain-google-vertexai`.See the full release notes and migration guide for details.

Nov 25, 2025 · langchain

## `langchain` v1.1.0

- Model profiles: Chat models now expose supported features and capabilities through a `.profile` attribute. These data are derived from models.dev, an open source project providing model capability data.
- Summarization middleware: Updated to support flexible trigger points using model profiles for context-aware summarization.
- Structured output: `ProviderStrategy` support (native structured output) can now be inferred from model profiles.
- `SystemMessage` for `create_agent`: Support for passing `SystemMessage` instances directly to `create_agent`’s `system_prompt` parameter, enabling advanced features like cache control and structured content blocks.
- Model retry middleware: New middleware for automatically retrying failed model calls with configurable exponential backoff.
- Content moderation middleware: OpenAI content moderation middleware for detecting and handling unsafe content in agent interactions. Supports checking user input, model output, and tool results.

Oct 20, 2025 · langchain, langgraph

## v1.0.0

### `langchain`

- Release notes
- Migration guide

### `langgraph`

- Release notes
- Migration guide

If you encounter any issues or have feedback, please open an issue so we can improve. To view v0.x documentation, go to the archived content and API reference.

---

[Edit this page on GitHub](https://github.com/langchain-ai/docs) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
