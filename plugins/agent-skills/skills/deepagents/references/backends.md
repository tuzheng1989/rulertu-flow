# Backends - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/backends

## Overview

Deep Agents expose a filesystem surface to the agent via tools like `ls`, `read_file`, `write_file`, `edit_file`, `glob`, and `grep`. These tools operate through a pluggable backend. The `read_file` tool natively supports image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`) across all backends, returning them as multimodal content blocks. Sandboxes and the `LocalShellBackend` also provide an `execute` tool.

This page explains how to:
- choose a backend
- route different paths to different backends
- implement your own virtual filesystem (e.g., S3 or Postgres)
- set permissions on filesystem access
- comply with the backend protocol

## Quickstart

Here are a few prebuilt filesystem backends that you can quickly use with your deep agent:

| Built-in backend | Description |
| --- | --- |
| Default | `agent = create_deep_agent(model="google_genai:gemini-3.1-pro-preview")`  Ephemeral in state. The default filesystem backend for an agent is stored in `langgraph` state. Note that this filesystem only persists _for a single thread_. |
| Local filesystem persistence | `agent = create_deep_agent(model="google_genai:gemini-3.1-pro-preview", backend=FilesystemBackend(root_dir="/Users/nh/Desktop/"))`  This gives the deep agent access to your local machine's filesystem. You can specify the root directory that the agent has access to. Note that any provided `root_dir` must be an absolute path. |
| Durable store (LangGraph store) | `agent = create_deep_agent(model="google_genai:gemini-3.1-pro-preview", backend=StoreBackend())`  This gives the agent access to long-term storage that is _persisted across threads_. This is great for storing longer term memories or instructions that are applicable to the agent over multiple executions. |
| Sandbox | `agent = create_deep_agent(model="google_genai:gemini-3.1-pro-preview", backend=sandbox)`  Execute code in isolated environments. Sandboxes provide filesystem tools plus the `execute` tool for running shell commands. Choose from Modal, Daytona, Deno, or local VFS. |
| Local shell | `agent = create_deep_agent(model="google_genai:gemini-3.1-pro-preview", backend=LocalShellBackend(root_dir=".", env={"PATH": "/usr/bin:/bin"}))`  Filesystem and shell execution directly on the host. No isolation—use only in controlled development environments. See security considerations below. |
| Composite | Ephemeral by default, `/memories/` persisted. The Composite backend is maximally flexible. You can specify different routes in the filesystem to point towards different backends. See Composite routing below for a ready-to-paste example. |

## Built-in backends

### StateBackend (ephemeral)

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

**How it works:**

- Stores files in LangGraph agent state for the current thread via `StateBackend`.
- Persists across multiple agent turns on the same thread via checkpoints.

**Best for:**

- A scratch pad for the agent to write intermediate results.
- Automatic eviction of large tool outputs which the agent can then read back in piece by piece.

Note that this backend is shared between the supervisor agent and subagents, and any files a subagent writes will remain in the LangGraph agent state even after that subagent's execution is complete. Those files will continue to be available to the supervisor agent and other subagents.

### FilesystemBackend (local disk)

`FilesystemBackend` reads and writes real files under a configurable root directory.

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=FilesystemBackend(root_dir=".", virtual_mode=True)
)
```

**How it works:**

- Reads/writes real files under a configurable `root_dir`.
- You can optionally set `virtual_mode=True` to sandbox and normalize paths under `root_dir`.
- Uses secure path resolution, prevents unsafe symlink traversal when possible, can use ripgrep for fast `grep`.

**Best for:**

- Local projects on your machine
- CI sandboxes
- Mounted persistent volumes

### LocalShellBackend (local shell)

```python
from deepagents.backends import LocalShellBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=LocalShellBackend(root_dir=".", env={"PATH": "/usr/bin:/bin"})
)
```

**How it works:**

- Extends `FilesystemBackend` with the `execute` tool for running shell commands on the host.
- Commands run directly on your machine using `subprocess.run(shell=True)` with no sandboxing.
- Supports `timeout` (default 120s), `max_output_bytes` (default 100,000), `env`, and `inherit_env` for environment variables.
- Shell commands use `root_dir` as the working directory but can access any path on the system.

**Best for:**

- Local coding assistants and development tools
- Quick iteration during development when you trust the agent

### StoreBackend (LangGraph store)

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

**How it works:**

- `StoreBackend` stores files in a LangGraph `BaseStore` provided by the runtime, enabling cross‑thread durable storage.

**Best for:**

- When you already run with a configured LangGraph store (for example, Redis, Postgres, or cloud implementations behind `BaseStore`).
- When you're deploying your agent through LangSmith Deployment (a store is automatically provisioned for your agent).

#### Namespace factories

A namespace factory controls where `StoreBackend` reads and writes data. It receives a LangGraph `Runtime` and returns a tuple of strings used as the store namespace. Use namespace factories to isolate data between users, tenants, or assistants.

Pass the namespace factory to the `namespace` parameter when constructing a `StoreBackend`:

```python
NamespaceFactory = Callable[[Runtime], tuple[str, ...]]
```

The `Runtime` provides:

- `rt.context` — User-supplied context passed via LangGraph's context schema (for example, `user_id`)
- `rt.server_info` — Server-specific metadata when running on LangGraph Server (assistant ID, graph ID, authenticated user)
- `rt.execution_info` — Execution identity information (thread ID, run ID, checkpoint ID)

**Common namespace patterns:**

```python
from deepagents.backends import StoreBackend

# Per-user: each user gets their own isolated storage
backend = StoreBackend(
    namespace=lambda rt: (rt.server_info.user.identity,),
)

# Per-assistant: all users of the same assistant share storage
backend = StoreBackend(
    namespace=lambda rt: (
        rt.server_info.assistant_id,
    ),
)

# Per-thread: storage scoped to a single conversation
backend = StoreBackend(
    namespace=lambda rt: (
        rt.execution_info.thread_id,
    ),
)
```

You can combine multiple components to create more specific scopes — for example, `(user_id, thread_id)` for per-user per-conversation isolation, or append a suffix like `"filesystem"` to disambiguate when the same scope uses multiple store namespaces.

Namespace components must contain only alphanumeric characters, hyphens, underscores, dots, `@`, `+`, colons, and tildes. Wildcards (`*`, `?`) are rejected to prevent glob injection.

### CompositeBackend (router)

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend()},
    ),
    store=InMemoryStore()  # Store passed to create_deep_agent, not backend
)
```

**How it works:**

- `CompositeBackend` routes file operations to different backends based on path prefix.
- Preserves the original path prefixes in listings and search results.

**Best for:**

- When you want to give your agent both ephemeral and cross-thread storage, a `CompositeBackend` allows you provide both a `StateBackend` and `StoreBackend`
- When you have multiple sources of information that you want to provide to your agent as part of a single filesystem.
  - e.g. You have long-term memories stored under `/memories/` in one Store and you also have a custom backend that has documentation accessible at /docs/.

## Specify a backend

- Pass a backend instance to `create_deep_agent(model=..., backend=...)`. The filesystem middleware uses it for all tooling.
- The backend must implement `BackendProtocol` (for example, `StateBackend()`, `FilesystemBackend(root_dir=".")`, `StoreBackend()`).
- If omitted, the default is `StateBackend()`.

## Route to different backends

Route parts of the namespace to different backends. Commonly used to persist `/memories/*` and keep everything else ephemeral.

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": FilesystemBackend(root_dir="/deepagents/myagent", virtual_mode=True),
        },
    ),
)
```

**Behavior:**

- `/workspace/plan.md` → `StateBackend` (ephemeral)
- `/memories/agent.md` → `FilesystemBackend` under `/deepagents/myagent`
- `ls`, `glob`, `grep` aggregate results and show original path prefixes.

**Notes:**

- Longer prefixes win (for example, route `"/memories/projects/"` can override `"/memories/"`).
- For StoreBackend routing, ensure a store is provided via `create_deep_agent(model=..., store=...)` or provisioned by the platform.
- Permissions that include paths outside any route raise `NotImplementedError` when using a sandbox default.

## Use a virtual filesystem

Build a custom backend to project a remote or database filesystem (e.g., S3 or Postgres) into the tools namespace.

**Design guidelines:**

- Paths are absolute (`/x/y.txt`). Decide how to map them to your storage keys/rows.
- Implement `ls` and `glob` efficiently (server-side filtering where available, otherwise local filter).
- For external persistence (S3, Postgres, etc.), return `files_update=None` (Python) or omit `filesUpdate` (JS) in write/edit results — only in-memory state backends need to return a files update dict.
- Use `ls` and `glob` as the method names. Return structured result types with an `error` field for missing files or invalid patterns (do not raise).

**S3-style outline:**

```python
from deepagents.backends.protocol import (
    BackendProtocol, WriteResult, EditResult, LsResult, ReadResult, GrepResult, GlobResult,
)

class S3Backend(BackendProtocol):
    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def _key(self, path: str) -> str:
        return f"{self.prefix}{path}"

    def ls(self, path: str) -> LsResult:
        # List objects under _key(path); build FileInfo entries (path, size, modified_at)
        ...

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        # Fetch object; return ReadResult(file_data=...) or ReadResult(error=...)
        ...

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None) -> GrepResult:
        # Optionally filter server-side; else list and scan content
        ...

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        # Apply glob relative to path across keys
        ...

    def write(self, file_path: str, content: str) -> WriteResult:
        # Enforce create‑only semantics; return WriteResult(path=file_path, files_update=None)
        ...

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        # Read → replace (respect uniqueness vs replace_all) → write → return occurrences
        ...
```

**Postgres-style outline:**

- Table `files(path text primary key, content text, created_at timestamptz, modified_at timestamptz)`
- Map tool operations onto SQL:
  - `ls` uses `WHERE path LIKE $1 || '%'`
  - `glob` uses `WHERE path LIKE $1` with pattern matching
  - `grep` uses full-text search (`WHERE content LIKE $1`) or extension-based filtering
  - `read` fetches by path
  - `write` creates new rows (enforce create-only via conflict check)
  - `edit` uses text replacement

## Permissions

Use permissions to declaratively control which files and directories an agent can read or write. Permissions apply to the built-in filesystem tools and are evaluated before the backend is called.

```python
from deepagents import create_deep_agent, FilesystemPermission

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
            "/policies/": StoreBackend(
                namespace=lambda rt: (rt.context.org_id,),
            ),
        },
    ),
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/policies/**"],
            mode="deny",
        ),
    ],
)
```

For the full set of options including rule ordering, subagent permissions, and composite backend interactions, see the permissions guide.

## Add policy hooks

For custom validation logic beyond path-based allow/deny rules (rate limiting, audit logging, content inspection), enforce enterprise rules by subclassing or wrapping a backend.

**Block writes/edits under selected prefixes (subclass):**

```python
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import WriteResult, EditResult

class GuardedBackend(FilesystemBackend):
    def __init__(self, *, deny_prefixes: list[str], **kwargs):
        super().__init__(**kwargs)
        self.deny_prefixes = [p if p.endswith("/") else p + "/" for p in deny_prefixes]

    def write(self, file_path: str, content: str) -> WriteResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return WriteResult(error=f"Writes are not allowed under {file_path}")
        return super().write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return EditResult(error=f"Edits are not allowed under {file_path}")
        return super().edit(file_path, old_string, new_string, replace_all)
```

**Generic wrapper (works with any backend):**

```python
from deepagents.backends.protocol import (
    BackendProtocol, WriteResult, EditResult, LsResult, ReadResult, GrepResult, GlobResult,
)

class PolicyWrapper(BackendProtocol):
    def __init__(self, inner: BackendProtocol, deny_prefixes: list[str] | None = None):
        self.inner = inner
        self.deny_prefixes = [p if p.endswith("/") else p + "/" for p in (deny_prefixes or [])]

    def _deny(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.deny_prefixes)

    def ls(self, path: str) -> LsResult:
        return self.inner.ls(path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        return self.inner.read(file_path, offset=offset, limit=limit)

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None) -> GrepResult:
        return self.inner.grep(pattern, path, glob)

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        return self.inner.glob(pattern, path)

    def write(self, file_path: str, content: str) -> WriteResult:
        if self._deny(file_path):
            return WriteResult(error=f"Writes are not allowed under {file_path}")
        return self.inner.write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        if self._deny(file_path):
            return EditResult(error=f"Edits are not allowed under {file_path}")
        return self.inner.edit(file_path, old_string, new_string, replace_all)
```

## Migrate from backend factories

Previously, backends like `StateBackend` and `StoreBackend` required a factory function that received a runtime object, because they needed runtime context (state, store) to operate. Backends now resolve this context internally via LangGraph's `get_config()`, `get_store()`, and `get_runtime()` helpers, so you can pass instances directly.

### What changed

| Before (deprecated) | After |
| --- | --- |
| `backend=lambda rt: StateBackend(rt)` | `backend=StateBackend()` |
| `backend=lambda rt: StoreBackend(rt)` | `backend=StoreBackend()` |
| `backend=lambda rt: CompositeBackend(default=StateBackend(rt), ...)` | `backend=CompositeBackend(default=StateBackend(), ...)` |
| `backend: (config) => new StateBackend(config)` | `backend: new StateBackend()` |
| `backend: (config) => new StoreBackend(config)` | `backend: new StoreBackend()` |

### Deprecated APIs

| Deprecated | Replacement |
| --- | --- |
| Passing a callable to `backend=` in `create_deep_agent` | Pass a backend instance directly |
| `runtime` constructor argument on `StateBackend(runtime)` | `StateBackend()` (no arguments needed) |
| `runtime` constructor argument on `StoreBackend(runtime)` | `StoreBackend()` or `StoreBackend(namespace=..., store=...)` |
| `files_update` field on `WriteResult` and `EditResult` | State writes are now handled internally by the backend |
| `Command` wrapping in middleware write/edit tools | Tools return plain strings; no `Command(update=...)` needed |

### Migration example

```python
# Before (deprecated)
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt, namespace=lambda rt: (rt.server_info.user.identity,))},
    ),
)

# After
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))},
    ),
)
```

### Migrating from `BackendContext`

In `deepagents>=0.5.2` (Python) and `deepagents>=1.9.1` (TypeScript), namespace factories receive a LangGraph `Runtime` directly instead of a `BackendContext` wrapper. The old `BackendContext` form still works via backwards-compatible `.runtime` and `.state` accessors, but those accessors emit a deprecation warning and will be removed in `deepagents>=0.7`.

**What changed:**

- The factory argument is now a `Runtime`, not a `BackendContext`.
- Drop the `.runtime` accessor — for example, `ctx.runtime.context.user_id` becomes `rt.server_info.user.identity`.
- There is no direct replacement for `ctx.state`. Namespace info should be read-only and stable for the lifetime of a run, whereas state is mutable and changes step-to-step—deriving a namespace from it risks data ending up under inconsistent keys. If you have a use case that requires reading agent state, please open an issue.

```python
# Before (deprecated, removed in v0.7)
StoreBackend(
    namespace=lambda ctx: (ctx.runtime.context.user_id,),
)

# After
StoreBackend(
    namespace=lambda rt: (rt.server_info.user.identity,),
)
```

## Protocol reference

Backends must implement `BackendProtocol`.

**Required methods:**

- `ls(path: str) -> LsResult`
  - Return entries with at least `path`. Include `is_dir`, `size`, `modified_at` when available. Sort by `path` for deterministic output.
- `read(file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult`
  - Return file data on success. On missing file, return `ReadResult(error="Error: File '/x' not found")`.
- `grep(pattern: str, path: Optional[str] = None, glob: Optional[str] = None) -> GrepResult`
  - Return structured matches. On error, return `GrepResult(error="...")` (do not raise).
- `glob(pattern: str, path: str = "/") -> GlobResult`
  - Return matched files as `FileInfo` entries (empty list if none).
- `write(file_path: str, content: str) -> WriteResult`
  - Create-only. On conflict, return `WriteResult(error=...)`. On success, set `path` and for state backends set `files_update={...}`; external backends should use `files_update=None`.
- `edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult`
  - Enforce uniqueness of `old_string` unless `replace_all=True`. If not found, return error. Include `occurrences` on success.

**Supporting types:**

- `LsResult(error, entries)` — `entries` is a `list[FileInfo]` on success, `None` on failure.
- `ReadResult(error, file_data)` — `file_data` is a `FileData` dict on success, `None` on failure.
- `GrepResult(error, matches)` — `matches` is a `list[GrepMatch]` on success, `None` on failure.
- `GlobResult(error, matches)` — `matches` is a `list[FileInfo]` on success, `None` on failure.
- `WriteResult(error, path, files_update)` — `files_update` dict for state backends.
- `EditResult(error, path, files_update, occurrences)` — `files_update` dict for state backends, `occurrences` count.

- `FileInfo` with fields: `path` (required), optionally `is_dir`, `size`, `modified_at`.
- `GrepMatch` with fields: `path`, `line`, `text`.
- `FileData` with fields: `content` (str), `encoding` (`"utf-8"` or `"base64"`), optionally `created_at`, `modified_at`.
