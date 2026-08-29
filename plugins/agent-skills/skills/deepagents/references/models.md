# Models - Deep Agents

Source: https://docs.langchain.com/oss/python/deepagents/models

## Overview

Deep Agents work with any LangChain chat model that supports tool calling.

## Supported models

Specify models in `provider:model` format (for example, `google_genai:gemini-3.1-pro-preview`, `openai:gpt-5.4`, or `anthropic:claude-sonnet-4-6`). For valid provider strings, see the `model_provider` parameter of `init_chat_model`. For provider-specific configuration, see chat model integrations.

## Suggested models

These models perform well on the Deep Agents eval suite, which tests basic agent operations. Passing these evals is necessary but not sufficient for strong performance on longer, more complex tasks.

| Provider | Models |
| --- | --- |
| Google | `gemini-3.1-pro-preview`, `gemini-3-flash-preview` |
| OpenAI | `gpt-5.4`, `gpt-4o`, `gpt-4.1`, `o4-mini`, `gpt-5.2-codex`, `gpt-4o-mini`, `o3` |
| Anthropic | `claude-opus-4-6`, `claude-opus-4-5`, `claude-sonnet-4-6`, `claude-sonnet-4`, `claude-sonnet-4-5`, `claude-haiku-4-5`, `claude-opus-4-1` |
| Open-weight | `GLM-5`, `Kimi-K2.5`, `MiniMax-M2.5`, `qwen3.5-397B-A17B`, `devstral-2-123B` |

Open-weight models are available through providers like Baseten, Fireworks, OpenRouter, and Ollama.

## Configure model parameters

Pass a model string to `create_deep_agent` in `provider:model` format, or pass a configured model instance for full control. Under the hood, model strings are resolved via `init_chat_model`.

To configure model-specific parameters, use `init_chat_model` or instantiate a provider model class directly.

## Select a model at runtime

If your application lets users choose a model (for example using a dropdown in the UI), use middleware to swap the model at runtime without rebuilding the agent.

Pass the user's model selection through runtime context, then use a `wrap_model_call` middleware to override the model on each invocation using the `@wrap_model_call` decorator:

```python
from dataclasses import dataclass
from langchain.chat_models import init_chat_model
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from deepagents import create_deep_agent
from typing import Callable

@dataclass
class Context:
    model: str

@wrap_model_call
def configurable_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    model_name = request.runtime.context.model
    model = init_chat_model(model_name)
    return handler(request.override(model=model))

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    middleware=[configurable_model],
    context_schema=Context,
)

# Invoke with the user's model selection
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Hello!"}]},
    context=Context(model="openai:gpt-5.4"),
)
```

## Connection resilience

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
