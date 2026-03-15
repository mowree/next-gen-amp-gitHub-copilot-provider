# Python Architecture: GitHub Copilot Provider Decomposition

**Wave 1, Round 1 — Python Architecture Expert**

---

## Executive Summary

A 1700-line `provider.py` is an AI-hostile monolith. Any agent editing it must hold the entire context window to understand even a single function. The fix is surgical decomposition into modules with single responsibilities, explicit interfaces, and zero circular dependencies. Each resulting module should fit comfortably within 300–500 lines so an AI agent can read it in full without truncation.

---

## 1. Module Decomposition

### Current State Problem

A monolithic `provider.py` typically accumulates:
- Authentication and credential management
- HTTP client setup and retry logic
- Request/response transformation
- Streaming buffer management
- Tool call parsing
- Token counting
- Error translation
- Configuration loading
- Async lifecycle management

These concerns are entangled. Changing the streaming buffer breaks token counting tests. Adding a new tool call format requires touching authentication code. This is the AI-hostile design: local changes have non-local effects.

### Target Module Structure

```
provider_github_copilot/
├── __init__.py                  # Public API surface only
├── provider.py                  # Thin orchestration layer (~150 lines)
├── auth/
│   ├── __init__.py
│   ├── token_manager.py         # Token refresh, caching, expiry (~200 lines)
│   └── credentials.py           # Credential loading from env/config (~100 lines)
├── client/
│   ├── __init__.py
│   ├── http_client.py           # aiohttp session, retry, timeout (~200 lines)
│   └── rate_limiter.py          # Rate limit tracking and backoff (~150 lines)
├── models/
│   ├── __init__.py
│   ├── request.py               # Amplifier → Copilot request transformation (~200 lines)
│   ├── response.py              # Copilot → Amplifier response transformation (~200 lines)
│   └── types.py                 # Shared type definitions, no logic (~100 lines)
├── streaming/
│   ├── __init__.py
│   ├── parser.py                # SSE/chunk parsing (~200 lines)
│   └── assembler.py             # Stream assembly, tool call reconstruction (~250 lines)
├── tools/
│   ├── __init__.py
│   └── tool_call_parser.py      # Tool call JSON extraction and validation (~200 lines)
├── config/
│   ├── __init__.py
│   └── settings.py              # Configuration dataclasses and loading (~150 lines)
└── errors/
    ├── __init__.py
    └── exceptions.py            # Exception hierarchy and translation (~150 lines)
```

### Dependency Graph

```
provider.py
    ├── config/settings.py          (no deps on other modules)
    ├── errors/exceptions.py        (no deps on other modules)
    ├── auth/credentials.py         → config/settings.py
    ├── auth/token_manager.py       → auth/credentials.py, errors/exceptions.py
    ├── client/rate_limiter.py      → errors/exceptions.py
    ├── client/http_client.py       → auth/token_manager.py, client/rate_limiter.py, errors/exceptions.py
    ├── models/types.py             (no deps on other modules)
    ├── models/request.py           → models/types.py, config/settings.py
    ├── models/response.py          → models/types.py, errors/exceptions.py
    ├── tools/tool_call_parser.py   → models/types.py, errors/exceptions.py
    ├── streaming/parser.py         → models/types.py, errors/exceptions.py
    └── streaming/assembler.py      → streaming/parser.py, tools/tool_call_parser.py, models/types.py
```

**Key rule**: arrows only point DOWN the list. `config` and `errors` are leaf dependencies — nothing they import comes from this package. This is non-negotiable.

### Circular Dependency Prevention

The most common circular dependency trap: `models/types.py` imports from `errors/exceptions.py` which imports from `models/types.py` for type hints. Prevention:

1. **`models/types.py` has zero imports from this package.** It defines only dataclasses and TypedDicts using stdlib types.
2. **`errors/exceptions.py` has zero imports from this package.** Exception classes accept `str` and `dict`, not domain types.
3. **`from __future__ import annotations`** in every file. This makes all annotations strings at runtime, breaking runtime circular import failures from forward references.
4. **Protocol classes** live in the module that *consumes* the protocol, not the module that *implements* it. This is the inversion that kills most circular deps.

---

## 2. Interface Design

### Protocol Classes

Use `typing.Protocol` for every cross-module dependency. This enables testing with mock objects and prevents tight coupling.

```python
# client/http_client.py — defines what it needs from auth
from typing import Protocol

class TokenProvider(Protocol):
    """Anything that can produce a Bearer token."""
    async def get_token(self) -> str: ...
    async def refresh_token(self) -> str: ...


# streaming/assembler.py — defines what it needs from parser
class ChunkParser(Protocol):
    """Anything that can parse a raw SSE line into a chunk."""
    def parse_line(self, line: str) -> StreamChunk | None: ...
    def is_done(self, line: str) -> bool: ...
```

**Why Protocols over ABCs**: ABCs require inheritance, which creates a dependency. Protocols require only structural compatibility — `auth/token_manager.py` doesn't need to import `client/http_client.py` to satisfy `TokenProvider`.

### Type Hints

All public functions require complete type hints. No `Any` in public interfaces. Internal helpers may use `Any` sparingly with a comment explaining why.

```python
# Good: complete signature
async def transform_request(
    messages: list[Message],
    config: CopilotConfig,
    *,
    stream: bool = False,
) -> CopilotRequest:
    ...

# Bad: missing return type, bare list
async def transform_request(messages: list, config) -> dict:
    ...
```

Use `TypeVar` and `Generic` when a function works on multiple types:

```python
T = TypeVar("T")

async def with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
) -> T:
    ...
```

### Dependency Injection Pattern

The `provider.py` orchestration layer wires all modules together. Dependencies flow in through `__init__`, not through global state or module-level singletons.

```python
# provider.py — explicit dependency wiring
class GitHubCopilotProvider:
    def __init__(
        self,
        config: CopilotConfig,
        *,
        token_manager: TokenProvider | None = None,
        http_client: HttpClientProtocol | None = None,
    ) -> None:
        self._config = config
        # Allow injection for testing; build production defaults otherwise
        self._token_manager = token_manager or TokenManager(config)
        self._http_client = http_client or CopilotHttpClient(
            token_provider=self._token_manager,
            config=config,
        )
```

This pattern means: production code uses real implementations; tests inject fakes without patching.

---

## 3. Error Handling Strategy

### Exception Hierarchy

```python
# errors/exceptions.py

class CopilotProviderError(Exception):
    """Base for all errors raised by this provider."""
    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class AuthenticationError(CopilotProviderError):
    """Token is missing, invalid, or expired and could not be refreshed."""


class RateLimitError(CopilotProviderError):
    """Rate limit hit. Includes retry-after when available."""
    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.retry_after_seconds = retry_after_seconds


class ModelNotFoundError(CopilotProviderError):
    """Requested model is not available in this Copilot subscription."""
    def __init__(self, message: str, *, model_id: str, cause: Exception | None = None) -> None:
        super().__init__(message, cause=cause)
        self.model_id = model_id


class StreamError(CopilotProviderError):
    """Error during streaming — connection lost, malformed chunk, etc."""


class RequestTransformError(CopilotProviderError):
    """Could not transform Amplifier request to Copilot format."""


class ResponseTransformError(CopilotProviderError):
    """Could not transform Copilot response to Amplifier format."""


class ToolCallParseError(CopilotProviderError):
    """Tool call JSON was malformed or incomplete."""
```

### SDK Error Translation

Each module translates its own errors at the boundary. HTTP errors are translated in `http_client.py`, not bubbled up as raw `aiohttp` exceptions.

```python
# client/http_client.py
async def _post(self, url: str, payload: dict) -> aiohttp.ClientResponse:
    try:
        response = await self._session.post(url, json=payload)
        await self._check_response_status(response)
        return response
    except aiohttp.ClientConnectionError as e:
        raise StreamError(f"Connection failed: {url}", cause=e) from e
    except aiohttp.ClientResponseError as e:
        raise self._translate_http_error(e) from e

def _translate_http_error(self, e: aiohttp.ClientResponseError) -> CopilotProviderError:
    if e.status == 401:
        return AuthenticationError("Invalid or expired token", cause=e)
    if e.status == 429:
        retry_after = self._parse_retry_after(e.headers)
        return RateLimitError("Rate limit exceeded", retry_after_seconds=retry_after, cause=e)
    if e.status == 404:
        return ModelNotFoundError(f"Model not found", model_id=self._last_model_id, cause=e)
    return CopilotProviderError(f"HTTP {e.status}: {e.message}", cause=e)
```

**Rule**: callers of `http_client.py` only need to catch `CopilotProviderError` subclasses. `aiohttp` never leaks through the module boundary.

---

## 4. Async Patterns

### Task Management

Never create bare `asyncio.create_task()` without tracking it. Untracked tasks cause silent failures and resource leaks.

```python
# Pattern: tracked task set
class GitHubCopilotProvider:
    def __init__(self, ...) -> None:
        self._background_tasks: set[asyncio.Task] = set()

    def _create_task(self, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
```

### Cancellation Handling

Every `async for` over a stream must handle `asyncio.CancelledError` explicitly:

```python
# streaming/assembler.py
async def assemble_stream(
    self,
    raw_stream: AsyncIterator[bytes],
) -> AsyncIterator[StreamChunk]:
    try:
        async for line in self._read_lines(raw_stream):
            chunk = self._parser.parse_line(line)
            if chunk is not None:
                yield chunk
    except asyncio.CancelledError:
        # Clean cancellation — do not suppress, re-raise after cleanup
        raise
    except Exception as e:
        raise StreamError("Stream assembly failed", cause=e) from e
```

**Rule**: `CancelledError` is always re-raised. Never `except Exception` catches it — use `except (Exception, BaseException)` only if you need to and immediately re-raise.

### Resource Cleanup

Use `contextlib.asynccontextmanager` for all resource-owning classes:

```python
# client/http_client.py
class CopilotHttpClient:
    async def __aenter__(self) -> "CopilotHttpClient":
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
```

The `provider.py` orchestration layer is itself a context manager that delegates to its dependencies. This creates a clean teardown chain.

### Async Generator Cleanup

When yielding from async generators in streaming responses, always use `try/finally` to ensure cleanup even if the consumer abandons iteration:

```python
async def stream_completion(self, request: CopilotRequest) -> AsyncIterator[ResponseChunk]:
    response = await self._http_client.post_stream(request)
    try:
        async for chunk in self._assembler.assemble_stream(response.content):
            yield chunk
    finally:
        # Ensure connection is returned to pool even if consumer breaks early
        response.release()
```

---

## 5. Configuration Management

### Configuration Dataclasses

All configuration is immutable once loaded. Use `@dataclass(frozen=True)` to enforce this.

```python
# config/settings.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthConfig:
    """Authentication configuration. All fields have defaults via env vars."""
    token: str = ""
    token_refresh_url: str = "https://api.github.com/copilot_internal/v2/token"
    token_ttl_seconds: int = 1740  # 29 minutes; token expires at 30


@dataclass(frozen=True)
class HttpConfig:
    """HTTP client configuration."""
    base_url: str = "https://api.githubcopilot.com"
    timeout_seconds: float = 60.0
    max_retries: int = 3
    retry_backoff_factor: float = 1.5
    connect_timeout_seconds: float = 10.0


@dataclass(frozen=True)
class CopilotConfig:
    """Root configuration object. Single source of truth."""
    auth: AuthConfig = field(default_factory=AuthConfig)
    http: HttpConfig = field(default_factory=HttpConfig)
    default_model: str = "gpt-4o"
    max_tokens_default: int = 4096
```

### Configuration Loading

Configuration loads from environment variables in a single function. This is the only place `os.environ` is touched.

```python
# config/settings.py
import os


def load_config_from_env() -> CopilotConfig:
    """
    Load configuration from environment variables.
    
    Environment variables:
        GITHUB_TOKEN: GitHub token for Copilot authentication
        COPILOT_BASE_URL: Override the Copilot API base URL
        COPILOT_TIMEOUT: Request timeout in seconds (float)
        COPILOT_DEFAULT_MODEL: Default model ID
    """
    return CopilotConfig(
        auth=AuthConfig(
            token=os.environ.get("GITHUB_TOKEN", ""),
        ),
        http=HttpConfig(
            base_url=os.environ.get("COPILOT_BASE_URL", "https://api.githubcopilot.com"),
            timeout_seconds=float(os.environ.get("COPILOT_TIMEOUT", "60.0")),
        ),
        default_model=os.environ.get("COPILOT_DEFAULT_MODEL", "gpt-4o"),
    )
```

### Runtime Overrides

The provider accepts runtime overrides via a separate `RequestConfig` that is per-request, not per-instance:

```python
# models/types.py
@dataclass(frozen=True)
class RequestConfig:
    """Per-request configuration overrides. None means use provider default."""
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = True
```

This separation is critical: `CopilotConfig` is set once at startup, `RequestConfig` varies per call. Mixing them leads to thread-safety bugs and confusing defaults.

---

## 6. Code Style for AI

An AI agent reading your code should be able to understand what a function does without executing it. The following conventions make this possible.

### Module-Level Docstrings

Every module starts with a docstring that answers three questions: what it does, what it does NOT do, and what its dependencies are.

```python
"""
Token manager for GitHub Copilot API authentication.

Responsibilities:
- Cache the short-lived Copilot API token (expires ~30 min)
- Refresh the token before it expires using the GitHub OAuth token
- Provide thread-safe token access for concurrent requests

NOT responsible for:
- Loading the GitHub OAuth token from environment (see auth/credentials.py)
- HTTP connection management (see client/http_client.py)

Dependencies:
- auth/credentials.py: CredentialStore protocol
- errors/exceptions.py: AuthenticationError
"""
```

### Function Docstrings

Every public function documents its failure modes explicitly:

```python
async def get_token(self) -> str:
    """
    Return a valid Copilot API token, refreshing if necessary.

    Returns:
        Bearer token string (without "Bearer " prefix).

    Raises:
        AuthenticationError: If the GitHub token is missing, invalid,
            or if the refresh endpoint returns a non-200 status.
        RateLimitError: If the token refresh endpoint is rate-limited.
    """
```

### Naming Patterns

| Pattern | Convention | Example |
|---|---|---|
| Async function | `async def verb_noun` | `async def fetch_token` |
| Sync transformation | `def transform_noun` | `def transform_request` |
| Predicate | `def is_noun` or `def has_noun` | `def is_expired`, `def has_tool_calls` |
| Factory | `def make_noun` or `def build_noun` | `def make_session`, `def build_headers` |
| Private helper | `_verb_noun` | `_parse_retry_after` |
| Protocol class | `NounVerber` or `NounProtocol` | `TokenProvider`, `ChunkParser` |
| Config dataclass | `NounConfig` | `AuthConfig`, `HttpConfig` |

### Comment Conventions

**Comments explain WHY, not WHAT.** If the code is clear, no comment is needed.

```python
# Good: explains non-obvious behavior
# Token TTL is 1800s but we refresh at 1740s to avoid races
# between the check and the actual API call.
TOKEN_REFRESH_BUFFER_SECONDS = 60

# Bad: restates the code
# Set the token TTL to 1740
TOKEN_TTL = 1740
```

For AI-specific guidance, use `# AI NOTE:` comments to flag areas that require context beyond the local scope:

```python
# AI NOTE: This function must remain synchronous. The token refresh loop
# calls it from a thread executor context where asyncio is not available.
def _read_cached_token(self) -> str | None:
    ...
```

### Constant Extraction

Magic numbers are AI-hostile. Every constant that appears more than once, or that a future engineer might want to change, gets a named module-level constant with a comment:

```python
# GitHub Copilot tokens expire after 30 minutes; refresh 60s early to avoid races
_TOKEN_TTL_SECONDS = 1740

# Copilot API SSE termination sentinel
_SSE_DONE_SENTINEL = "[DONE]"

# Maximum chunks to buffer before yielding to avoid memory pressure
_STREAM_BUFFER_MAX_CHUNKS = 32
```

### File Size Discipline

Each module has a soft limit of 400 lines and a hard limit of 600 lines. When a file approaches 400 lines:
1. Identify the natural split point (classes, groups of related functions)
2. Extract to a submodule
3. Re-export from the original `__init__.py` to preserve the public API

This ensures an AI agent can always read an entire module in one context window.

---

## 7. The `provider.py` Orchestration Layer

After decomposition, the root `provider.py` becomes a thin orchestrator. Its only job is wiring and delegating:

```python
"""
GitHub Copilot provider for Amplifier.

This module is the entry point and orchestrator. It:
- Wires together all sub-modules
- Implements the Amplifier provider protocol
- Manages the async lifecycle (startup, shutdown, context management)

For implementation details, see:
- auth/token_manager.py     — token refresh
- client/http_client.py     — HTTP transport
- models/request.py         — request transformation
- streaming/assembler.py    — response streaming
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType

from .auth.token_manager import TokenManager
from .client.http_client import CopilotHttpClient
from .config.settings import CopilotConfig, load_config_from_env
from .errors.exceptions import CopilotProviderError
from .models.request import transform_request
from .models.response import transform_response
from .models.types import Message, RequestConfig, ResponseChunk
from .streaming.assembler import StreamAssembler


class GitHubCopilotProvider:
    """
    Amplifier provider implementation for GitHub Copilot.
    
    Usage:
        async with GitHubCopilotProvider.from_env() as provider:
            async for chunk in provider.stream_chat(messages, config):
                process(chunk)
    """

    def __init__(
        self,
        config: CopilotConfig,
        *,
        http_client: CopilotHttpClient | None = None,
    ) -> None:
        self._config = config
        self._token_manager = TokenManager(config.auth)
        self._http_client = http_client or CopilotHttpClient(
            token_provider=self._token_manager,
            config=config.http,
        )
        self._assembler = StreamAssembler()

    @classmethod
    def from_env(cls) -> "GitHubCopilotProvider":
        """Create provider from environment variables."""
        return cls(config=load_config_from_env())

    async def stream_chat(
        self,
        messages: list[Message],
        request_config: RequestConfig | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        """Stream a chat completion. See streaming/assembler.py for chunk format."""
        config = request_config or RequestConfig()
        copilot_request = transform_request(messages, self._config, config)
        raw_response = await self._http_client.post_stream(copilot_request)
        async for chunk in self._assembler.assemble_stream(raw_response):
            yield transform_response(chunk)

    async def __aenter__(self) -> "GitHubCopilotProvider":
        await self._http_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)
```

This file is ~80 lines. An AI agent can read it entirely, understand the full architecture, and navigate to the right submodule for any task.

---

## Summary: The Design Principles

1. **Leaf modules have no internal imports.** `config/` and `errors/` import only stdlib.
2. **Protocols, not imports.** Cross-module contracts are structural, not nominal.
3. **Frozen dataclasses for config.** Immutability prevents action-at-a-distance bugs.
4. **Translate errors at boundaries.** No raw SDK exceptions escape their module.
5. **Re-raise `CancelledError`.** Always. No exceptions.
6. **400-line soft limit per file.** AI-readable means AI-editable.
7. **`# AI NOTE:` for traps.** Flag non-obvious constraints explicitly.
8. **One env-reading function.** `load_config_from_env()` is the only place `os.environ` is used.
9. **Dependency injection at the root.** The provider wires; submodules don't reach up.
10. **Module docstrings answer three questions.** What, not-what, dependencies.
