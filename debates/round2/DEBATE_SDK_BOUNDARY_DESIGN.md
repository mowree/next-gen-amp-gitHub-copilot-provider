# DEBATE ROUND 2: Definitive SDK Boundary Design

**Agent**: Zen Architect (SDK Boundary Authority)
**Date**: 2026-03-08
**Inputs**: Kernel Philosophy (Wave 1), Dependency Management (Wave 2), Provider Comparison (Wave 3)
**Decision**: Contract-First with Adapter Translation

---

## Executive Decision

After synthesizing three independent analyses, the SDK boundary architecture is **Contract-First**: we define our own interfaces that express what Amplifier needs, and the adapter layer translates the SDK's reality into our contracts. This is neither a thin wrapper (too coupled) nor a blind adapter (too speculative). It is a **membrane** — a precisely defined boundary where SDK types are translated into domain types, SDK errors become domain errors, and SDK events become domain events.

The guiding principle: **No SDK type crosses the boundary. Ever.**

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AMPLIFIER CORE                           │
│                                                             │
│  ChatRequest ─► Provider Protocol ─► ChatResponse           │
│  (our types)    (our contract)       (our types)            │
│                                                             │
├─────────────────────── BOUNDARY ────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            SDK ADAPTER LAYER (membrane)              │   │
│  │                                                      │   │
│  │  Inbound:  ChatRequest → SDK session config          │   │
│  │  Outbound: SDK events → ContentBlock[]               │   │
│  │  Errors:   SDK exceptions → domain exceptions        │   │
│  │  Events:   SDK event types → domain event types      │   │
│  │  Types:    SDK types → NEVER cross this line         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            SDK DRIVER (containment)                  │   │
│  │                                                      │   │
│  │  Session lifecycle, subprocess management,           │   │
│  │  agent loop suppression, circuit breaker             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            @github/copilot-sdk (radioactive)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

Three distinct layers, each with a single responsibility:

1. **SDK Adapter Layer** — Translates between our domain types and SDK types. This is the membrane. It is the ONLY code that imports from `@github/copilot-sdk`.
2. **SDK Driver** — Manages the SDK subprocess lifecycle, session creation/destruction, agent loop suppression, and circuit breaking. It speaks in domain types (received from the adapter).
3. **Raw SDK** — The `@github/copilot-sdk` package. We treat it as radioactive material: essential but contained.

---

## 2. The Boundary Contract: Interface Definitions

### 2.1 Core Domain Types (Our Types — SDK-Free)

These types define what the provider exposes to Amplifier. They are stable, versioned, and contain zero SDK imports.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, AsyncIterator, Callable, Any


# ── Content Model ──────────────────────────────────────────

class ContentBlockType(Enum):
    """Every content type the provider can produce."""
    TEXT = "text"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"


class FinishReason(Enum):
    """Normalized finish reasons across all providers."""
    STOP = "stop"
    TOOL_USE = "tool_use"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Plain text content from the model."""
    text: str
    type: ContentBlockType = field(default=ContentBlockType.TEXT, init=False)


@dataclass(frozen=True, slots=True)
class ThinkingBlock:
    """Extended thinking content with signature for multi-turn preservation."""
    thinking: str
    signature: str | None = None
    type: ContentBlockType = field(default=ContentBlockType.THINKING, init=False)


@dataclass(frozen=True, slots=True)
class ToolCallBlock:
    """Structured tool call request."""
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    type: ContentBlockType = field(default=ContentBlockType.TOOL_CALL, init=False)


ContentBlock = TextBlock | ThinkingBlock | ToolCallBlock


@dataclass(frozen=True, slots=True)
class Usage:
    """Token usage metadata. None means 'not available', never fabricated."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    thinking_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """What a model can do. Reported uniformly across providers."""
    supports_tools: bool
    supports_vision: bool
    supports_streaming: bool
    supports_extended_thinking: bool
    context_window: int
    max_output_tokens: int
    reasoning_efforts: list[str] | None = None  # ["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """Model metadata returned by list_models()."""
    model_id: str
    display_name: str
    capabilities: ModelCapabilities
    provider: str  # "github-copilot"


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Provider metadata returned by get_info()."""
    name: str
    version: str
    models: list[ModelInfo]
```

### 2.2 The Provider Protocol (Immutable Contract)

```python
class CopilotProvider(Protocol):
    """The 5-method provider contract. Immutable."""

    @property
    def name(self) -> str: ...

    def get_info(self) -> ProviderInfo: ...

    async def list_models(self) -> list[ModelInfo]: ...

    async def complete(
        self,
        request: ChatRequest,
        *,
        on_content: Callable[[ContentDelta], None] | None = None,
    ) -> ChatResponse: ...

    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCallBlock]: ...
```

### 2.3 The Adapter Protocol (Internal Contract)

This is the contract between the provider logic and the SDK translation layer. It is internal — Amplifier never sees it.

```python
class SdkAdapter(Protocol):
    """
    Translation layer between domain types and the SDK.
    This is the ONLY code that imports from @github/copilot-sdk.
    """

    async def create_session(
        self, config: SessionConfig
    ) -> SessionHandle: ...

    async def send_message(
        self, session: SessionHandle, prompt: str, tools: list[ToolDefinition]
    ) -> AsyncIterator[DomainEvent]: ...

    async def destroy_session(self, session: SessionHandle) -> None: ...

    async def list_available_models(self) -> list[RawModelData]: ...

    async def health_check(self) -> bool: ...

    async def close(self) -> None: ...
```

Key design decisions:
- `SessionHandle` is an opaque token (not an SDK session object)
- `send_message` returns domain events, not SDK events
- `RawModelData` is a simple dict/dataclass, not an SDK type
- The adapter owns ALL SDK imports

---

## 3. Translation Strategy by SDK Type Category

### 3.1 Type Translation Table

Every SDK type that enters our system must be translated at the adapter boundary. Here is the exhaustive mapping:

```
SDK TYPE                          → DOMAIN TYPE                    STRATEGY
─────────────────────────────────   ─────────────────────────────  ────────────
copilot.Session                   → SessionHandle (opaque str)     Wrap ID only
copilot.Message                   → ContentBlock[]                 Decompose
copilot.TextContent               → TextBlock                     Direct map
copilot.ThinkingContent           → ThinkingBlock                 Map + extract signature
copilot.ToolUseContent            → ToolCallBlock                 Parse arguments
copilot.ToolResult                → (never enters; we deny all)   N/A
copilot.Model                     → ModelInfo                     Map fields
copilot.ModelCapability           → ModelCapabilities             Map fields
copilot.SessionConfig             → (built FROM SessionConfig)    Reverse map
copilot.ToolDefinition            → (built FROM ToolDefinition)   Reverse map
copilot.Event                     → DomainEvent                   Translate per type
copilot.Error (base)              → CopilotProviderError          Classify + wrap
copilot.AuthError                 → CopilotAuthError              Direct map
copilot.RateLimitError            → CopilotRateLimitError         Map + extract retry_after
copilot.TimeoutError              → CopilotTimeoutError           Direct map
copilot.ContentFilterError        → CopilotContentFilterError     Direct map
copilot.SessionCreateError        → CopilotSessionError           Direct map
copilot.PermissionHandler         → (configured internally)       Never exposed
copilot.Hook                      → (configured internally)       Never exposed
copilot.McpServer                 → (never used)                  Excluded
```

### 3.2 Translation Rules

**Rule 1: Decompose, Don't Wrap**

SDK types are decomposed into our primitives, never wrapped. A `copilot.Message` becomes a `list[ContentBlock]`, not a `MessageWrapper(sdk_message)`. This ensures that if the SDK changes `Message` internals, only the adapter's decomposition logic changes.

```python
# CORRECT: Decompose at boundary
def translate_message(sdk_msg: copilot.Message) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    for content in sdk_msg.content:
        match content:
            case copilot.TextContent(text=text):
                blocks.append(TextBlock(text=text))
            case copilot.ThinkingContent(thinking=thinking, signature=sig):
                blocks.append(ThinkingBlock(thinking=thinking, signature=sig))
            case copilot.ToolUseContent(id=id, name=name, input=args):
                blocks.append(ToolCallBlock(
                    tool_call_id=id, tool_name=name, arguments=args
                ))
    return blocks

# WRONG: Wrapping leaks SDK coupling
class MessageWrapper:
    def __init__(self, sdk_msg: copilot.Message):
        self._msg = sdk_msg  # SDK type lives beyond boundary!
```

**Rule 2: Opaque Handles for Stateful SDK Objects**

SDK objects with lifecycle (sessions, connections) are represented as opaque handles. The adapter maintains an internal mapping.

```python
@dataclass(frozen=True, slots=True)
class SessionHandle:
    """Opaque reference to an SDK session. Domain code never inspects internals."""
    id: str


class CopilotSdkAdapter:
    def __init__(self) -> None:
        self._sessions: dict[str, copilot.Session] = {}

    async def create_session(self, config: SessionConfig) -> SessionHandle:
        sdk_session = await self._client.create_session(
            self._to_sdk_config(config)
        )
        handle = SessionHandle(id=str(uuid4()))
        self._sessions[handle.id] = sdk_session
        return handle

    async def destroy_session(self, handle: SessionHandle) -> None:
        sdk_session = self._sessions.pop(handle.id)
        await sdk_session.destroy()
```

**Rule 3: Reverse Translation for Outbound Types**

When we send data TO the SDK (tool definitions, session config), we translate from our types to SDK types inside the adapter.

```python
def _to_sdk_tool(self, tool: ToolDefinition) -> copilot.ToolDefinition:
    """Translate our tool definition to SDK format. Lives ONLY in adapter."""
    return copilot.ToolDefinition(
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters_schema,
    )

def _to_sdk_config(self, config: SessionConfig) -> copilot.SessionConfig:
    """Translate our session config to SDK format. Lives ONLY in adapter."""
    return copilot.SessionConfig(
        model=config.model_id,
        system_prompt=config.system_prompt,
        max_tokens=config.max_output_tokens,
        # SDK-specific fields set here, invisible to domain code
        permissions=copilot.PermissionHandler.approve_all,
    )
```

---

## 4. Error Translation Table

Errors are the most critical boundary crossing. Every SDK exception must be caught in the adapter and re-raised as a domain exception. The domain exceptions carry:
- A `retryable` flag (mechanism provides; Amplifier policy decides whether to actually retry)
- An optional `retry_after` duration (extracted from SDK error metadata)
- The original error message (sanitized of SDK internals)

### 4.1 Error Hierarchy

```python
class CopilotProviderError(Exception):
    """Base error for all Copilot provider failures."""
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        retry_after: float | None = None,
        original: Exception | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after
        self.original = original


class CopilotAuthError(CopilotProviderError):
    """Authentication or authorization failure."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=False, **kwargs)


class CopilotRateLimitError(CopilotProviderError):
    """Rate limit exceeded. Always retryable with backoff."""
    def __init__(self, message: str, retry_after: float | None = None, **kwargs: Any):
        super().__init__(message, retryable=True, retry_after=retry_after, **kwargs)


class CopilotTimeoutError(CopilotProviderError):
    """Request timed out. Retryable."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=True, **kwargs)


class CopilotContentFilterError(CopilotProviderError):
    """Content policy violation. Not retryable."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=False, **kwargs)


class CopilotSessionError(CopilotProviderError):
    """Session creation or management failure. Retryable."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=True, **kwargs)


class CopilotModelNotFoundError(CopilotProviderError):
    """Requested model not available. Not retryable."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=False, **kwargs)


class CopilotSubprocessError(CopilotProviderError):
    """CLI subprocess crashed or is unreachable. Retryable (restart)."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=True, **kwargs)


class CopilotCircuitBreakerError(CopilotProviderError):
    """Agent loop exceeded safety limits. Not retryable."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, retryable=False, **kwargs)
```

### 4.2 Error Translation Map

This is the exhaustive mapping implemented inside the adapter's error boundary:

```
SDK EXCEPTION                     → DOMAIN EXCEPTION               RETRYABLE  RETRY_AFTER
─────────────────────────────────   ─────────────────────────────── ─────────  ───────────
copilot.AuthenticationError       → CopilotAuthError                No         —
copilot.InvalidTokenError         → CopilotAuthError                No         —
copilot.PermissionDeniedError     → CopilotAuthError                No         —
copilot.RateLimitError            → CopilotRateLimitError           Yes        Extract¹
copilot.QuotaExceededError        → CopilotRateLimitError           Yes        Extract¹
copilot.TimeoutError              → CopilotTimeoutError             Yes        —
copilot.RequestTimeoutError       → CopilotTimeoutError             Yes        —
copilot.ContentFilterError        → CopilotContentFilterError       No         —
copilot.SafetyError               → CopilotContentFilterError       No         —
copilot.ModelNotFoundError        → CopilotModelNotFoundError       No         —
copilot.ModelUnavailableError     → CopilotModelNotFoundError       No         —
copilot.SessionCreateError        → CopilotSessionError             Yes        —
copilot.SessionDestroyError       → CopilotSessionError             Yes        —
copilot.ConnectionError           → CopilotSubprocessError          Yes        —
copilot.ProcessExitedError        → CopilotSubprocessError          Yes        —
copilot.JSONRPCError (generic)    → CopilotProviderError            No         —
copilot.InternalError             → CopilotProviderError            Yes        —
Exception (unexpected)            → CopilotProviderError            No         —

¹ retry_after extracted via: error.retry_after or regex from error.message
```

### 4.3 Error Translation Implementation

```python
import re

_RETRY_AFTER_PATTERN = re.compile(r"retry.after\D*(\d+(?:\.\d+)?)", re.IGNORECASE)


def translate_sdk_error(exc: Exception) -> CopilotProviderError:
    """
    Translate ANY SDK exception to a domain exception.
    This function is the sole error boundary. It lives in the adapter.
    """
    # Auth errors — never retry
    if isinstance(exc, (copilot.AuthenticationError, copilot.InvalidTokenError,
                        copilot.PermissionDeniedError)):
        return CopilotAuthError(str(exc), original=exc)

    # Rate limits — always retry with extracted backoff
    if isinstance(exc, (copilot.RateLimitError, copilot.QuotaExceededError)):
        retry_after = getattr(exc, "retry_after", None)
        if retry_after is None:
            match = _RETRY_AFTER_PATTERN.search(str(exc))
            if match:
                retry_after = float(match.group(1))
        return CopilotRateLimitError(str(exc), retry_after=retry_after, original=exc)

    # Timeouts — retryable
    if isinstance(exc, (copilot.TimeoutError, copilot.RequestTimeoutError)):
        return CopilotTimeoutError(str(exc), original=exc)

    # Content filters — not retryable
    if isinstance(exc, (copilot.ContentFilterError, copilot.SafetyError)):
        return CopilotContentFilterError(str(exc), original=exc)

    # Model errors — not retryable
    if isinstance(exc, (copilot.ModelNotFoundError, copilot.ModelUnavailableError)):
        return CopilotModelNotFoundError(str(exc), original=exc)

    # Session errors — retryable (session can be recreated)
    if isinstance(exc, (copilot.SessionCreateError, copilot.SessionDestroyError)):
        return CopilotSessionError(str(exc), original=exc)

    # Subprocess/connection errors — retryable (subprocess can restart)
    if isinstance(exc, (copilot.ConnectionError, copilot.ProcessExitedError)):
        return CopilotSubprocessError(str(exc), original=exc)

    # Internal SDK errors — retryable (transient)
    if isinstance(exc, copilot.InternalError):
        return CopilotProviderError(str(exc), retryable=True, original=exc)

    # Catch-all — not retryable (unknown failure mode)
    return CopilotProviderError(
        f"Unexpected SDK error: {type(exc).__name__}: {exc}",
        retryable=False,
        original=exc,
    )
```

---

## 5. Event Translation Rules

The Copilot SDK emits ~58 event types. We translate only the ones we need into a small, stable domain event vocabulary.

### 5.1 Domain Event Types

```python
class DomainEventType(Enum):
    """Events the provider emits. Small, stable vocabulary."""
    CONTENT_DELTA = "content_delta"         # Incremental text/thinking
    TOOL_CALL = "tool_call"                 # Complete tool call captured
    USAGE_UPDATE = "usage_update"           # Token usage metadata
    TURN_COMPLETE = "turn_complete"         # Model finished a turn
    SESSION_IDLE = "session_idle"           # SDK reports idle (done)
    ERROR = "error"                         # Error during processing


@dataclass(frozen=True, slots=True)
class ContentDelta:
    """Incremental content for streaming."""
    block_type: ContentBlockType
    text: str
    block_index: int = 0


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """A single translated event from the SDK."""
    type: DomainEventType
    data: ContentDelta | ToolCallBlock | Usage | FinishReason | CopilotProviderError
```

### 5.2 SDK Event → Domain Event Mapping

```
SDK EVENT TYPE              → DOMAIN EVENT             ACTION
────────────────────────────  ────────────────────────  ────────────────────────
text_delta                  → CONTENT_DELTA(TEXT)       Emit streaming text
thinking_delta              → CONTENT_DELTA(THINKING)   Emit streaming thinking
tool_use_start              → (buffer internally)       Start accumulating tool call
tool_use_delta              → (buffer internally)       Accumulate arguments
tool_use_complete           → TOOL_CALL                 Emit complete tool call block
message_complete            → TURN_COMPLETE             Emit finish reason
usage_update                → USAGE_UPDATE              Emit token counts
session_idle                → SESSION_IDLE              Signal completion
error                       → ERROR                     Translate & emit

IGNORED SDK EVENTS (never translated):
────────────────────────────
tool_result_*               → Ignored (we deny all tool execution)
mcp_*                       → Ignored (we don't use MCP integration)
permission_*                → Ignored (approve-all configured)
context_*                   → Ignored (we manage our own context)
session_created             → Internal bookkeeping only
session_destroyed           → Internal bookkeeping only
heartbeat                   → Health check mechanism only
debug_*                     → Logging only, not domain events
```

### 5.3 Event Translation Implementation

```python
class EventTranslator:
    """Translates SDK events to domain events. Stateful for tool call accumulation."""

    def __init__(self) -> None:
        self._pending_tool: dict[str, Any] | None = None

    def translate(self, sdk_event: copilot.Event) -> DomainEvent | None:
        """
        Translate a single SDK event. Returns None for ignored events.
        """
        match sdk_event.type:
            case "text_delta":
                return DomainEvent(
                    type=DomainEventType.CONTENT_DELTA,
                    data=ContentDelta(
                        block_type=ContentBlockType.TEXT,
                        text=sdk_event.data.text,
                    ),
                )

            case "thinking_delta":
                return DomainEvent(
                    type=DomainEventType.CONTENT_DELTA,
                    data=ContentDelta(
                        block_type=ContentBlockType.THINKING,
                        text=sdk_event.data.thinking,
                    ),
                )

            case "tool_use_start":
                self._pending_tool = {
                    "id": sdk_event.data.id,
                    "name": sdk_event.data.name,
                    "arguments_json": "",
                }
                return None  # Buffer until complete

            case "tool_use_delta":
                if self._pending_tool:
                    self._pending_tool["arguments_json"] += sdk_event.data.delta
                return None  # Buffer until complete

            case "tool_use_complete":
                if self._pending_tool:
                    import json
                    tool = self._pending_tool
                    self._pending_tool = None
                    return DomainEvent(
                        type=DomainEventType.TOOL_CALL,
                        data=ToolCallBlock(
                            tool_call_id=tool["id"],
                            tool_name=tool["name"],
                            arguments=json.loads(tool["arguments_json"] or "{}"),
                        ),
                    )
                return None

            case "usage_update":
                return DomainEvent(
                    type=DomainEventType.USAGE_UPDATE,
                    data=Usage(
                        input_tokens=sdk_event.data.input_tokens,
                        output_tokens=sdk_event.data.output_tokens,
                        total_tokens=(
                            sdk_event.data.input_tokens + sdk_event.data.output_tokens
                        ),
                        thinking_tokens=getattr(sdk_event.data, "thinking_tokens", None),
                    ),
                )

            case "message_complete":
                return DomainEvent(
                    type=DomainEventType.TURN_COMPLETE,
                    data=_translate_finish_reason(sdk_event.data.stop_reason),
                )

            case "session_idle":
                return DomainEvent(
                    type=DomainEventType.SESSION_IDLE,
                    data=FinishReason.STOP,
                )

            case "error":
                return DomainEvent(
                    type=DomainEventType.ERROR,
                    data=translate_sdk_error(sdk_event.data.error),
                )

            case _:
                return None  # Ignored event type


def _translate_finish_reason(sdk_reason: str) -> FinishReason:
    """Map SDK stop reasons to our normalized set."""
    return {
        "end_turn": FinishReason.STOP,
        "stop": FinishReason.STOP,
        "tool_use": FinishReason.TOOL_USE,
        "max_tokens": FinishReason.LENGTH,
        "content_filter": FinishReason.CONTENT_FILTER,
    }.get(sdk_reason, FinishReason.ERROR)
```

---

## 6. Types That NEVER Cross the Boundary

These SDK types are absolutely forbidden from appearing in any public-facing signature, return type, parameter, or stored state outside the adapter module:

### 6.1 Forbidden Types (Complete List)

```
CATEGORY            FORBIDDEN TYPES                     WHY
────────────────    ──────────────────────────────────  ────────────────────────────
Session Objects     copilot.Session                     Lifecycle-bound, mutable
                    copilot.SessionConfig               SDK-specific config shape
                    copilot.SessionState                Internal SDK state

Content Types       copilot.Message                     SDK wire format
                    copilot.TextContent                 SDK content model
                    copilot.ThinkingContent             SDK content model
                    copilot.ToolUseContent              SDK content model
                    copilot.ToolResult                  We never produce these

Client Objects      copilot.CopilotClient               Subprocess handle
                    copilot.Connection                  Transport detail
                    copilot.JSONRPCTransport            Wire protocol detail

Hook/Permission     copilot.Hook                        SDK extension point
                    copilot.HookResult                  SDK-specific result
                    copilot.PermissionHandler           SDK permission model
                    copilot.PermissionRequest           SDK permission model

Event Types         copilot.Event                       Raw SDK event
                    copilot.EventData                   SDK event payload
                    copilot.EventSubscription           SDK subscription handle

Error Types         copilot.Error (any subclass)        Must be translated
                    copilot.JSONRPCError                Wire protocol error

MCP Types           copilot.McpServer                   We don't use MCP
                    copilot.McpTool                     We don't use MCP

Tool Types          copilot.BuiltinTool                 We exclude built-ins
                    copilot.ToolDefinition (SDK's)      We have our own
```

### 6.2 Enforcement Strategy

1. **Static analysis rule**: An ESLint/ruff rule that flags any import from `@github/copilot-sdk` outside the `sdk_adapter/` directory.
2. **Type checking**: Our domain types use no SDK types in their definitions. Pyright/mypy will catch leaks.
3. **Code review checklist item**: "Does this change import or reference SDK types outside the adapter?"
4. **Architecture fitness test**: A CI test that scans import statements and fails if SDK imports exist outside the adapter boundary.

```python
# tests/architecture/test_sdk_boundary.py
import ast
import pathlib

ADAPTER_DIR = "src/provider/sdk_adapter"
SDK_PACKAGE = "copilot"  # or "@github/copilot-sdk"

def test_sdk_imports_only_in_adapter():
    """SDK types must not leak beyond the adapter boundary."""
    src = pathlib.Path("src/provider")
    violations = []
    for py_file in src.rglob("*.py"):
        if ADAPTER_DIR in str(py_file):
            continue  # Adapter is allowed to import SDK
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", "") or ""
                names = [a.name for a in node.names]
                if SDK_PACKAGE in module or SDK_PACKAGE in names:
                    violations.append(f"{py_file}:{node.lineno}")
    assert not violations, f"SDK imports outside adapter: {violations}"
```

---

## 7. Why Contract-First (Not Thin Wrapper or Blind Adapter)

### 7.1 Thin Wrapper — Rejected

A thin wrapper mirrors the SDK's API surface. When the SDK adds `session.resume()`, the wrapper adds `session.resume()`. This creates **coupling by design** — our API surface grows and changes with the SDK.

**Why it fails for Copilot**: The SDK is an agentic runtime with 58 event types, 27 built-in tools, an internal agent loop, and session state management. Mirroring this surface would expose complexity that Amplifier must never see. The Copilot SDK is 5x more complex than Anthropic/OpenAI — a thin wrapper would amplify that complexity.

### 7.2 Blind Adapter — Rejected

A blind adapter translates everything without opinion. Every SDK type gets a mirror domain type. Every SDK event gets a mirror domain event. The adapter is a mechanical translator.

**Why it fails for Copilot**: Of 58 SDK event types, we need ~8. Of the SDK's full session API, we use create/send/destroy. A blind adapter would create 50+ unused domain types, violating YAGNI and creating maintenance burden for types that serve no consumer.

### 7.3 Contract-First — Selected

We define what Amplifier needs (6 domain event types, 3 content block types, 7 error types), then build the adapter to produce exactly that from whatever the SDK provides.

**Why it works for Copilot**:
- The 58→6 event reduction is intentional and stable
- Adding a new domain event is a deliberate design decision, not an SDK-driven reaction
- The adapter absorbs SDK churn without propagating it
- Testing is focused: we test that the adapter produces correct domain events, not that it mirrors SDK behavior

**The trade-off**: When the SDK adds genuinely useful new capabilities, we must explicitly decide to expose them by extending our domain types. This is a feature, not a bug — it forces conscious design decisions about our public API surface.

---

## 8. Architectural Fitness Metrics

To ensure the boundary remains healthy over time:

| Metric | Target | Alert Threshold | How to Measure |
|--------|--------|-----------------|----------------|
| Adapter line count | ≤500 | >700 | `wc -l sdk_adapter/*.py` |
| SDK import count | ≤12 | >18 | Count distinct SDK imports |
| Domain event types | ≤10 | >15 | Count `DomainEventType` members |
| Domain error types | ≤10 | >15 | Count `CopilotProviderError` subclasses |
| Boundary violations | 0 | >0 | Architecture fitness test in CI |
| SDK type references outside adapter | 0 | >0 | Static analysis |

---

## 9. Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Boundary pattern | Contract-First | We define our API; adapter translates SDK to it |
| SDK types in public API | Forbidden | Zero SDK types cross the boundary |
| Session representation | Opaque handle | Domain code never touches SDK session objects |
| Error strategy | Translate all + retryable flag | Adapter classifies; Amplifier decides retry policy |
| Event strategy | 58→6 reduction | Only translate events we consume |
| Content model | 3 block types | TextBlock, ThinkingBlock, ToolCallBlock |
| Enforcement | Static analysis + CI test | Automated boundary violation detection |
| Adapter scope | Single directory | All SDK imports confined to `sdk_adapter/` |

---

## 10. Relationship to Round 1 Findings

**From Kernel Philosophy (Wave 1)**: This design enforces the mechanism/policy separation. The adapter is pure mechanism (translation). Retry policy, timeout policy, and behavior correction remain Amplifier's responsibility. The adapter raises `retryable=True` errors — it never retries.

**From Dependency Management (Wave 2)**: The adapter IS the isolation architecture recommended. Exact SDK version pinning + adapter boundary means SDK upgrades are localized to one directory. The `sdk-surface.d.ts` concept maps to our architecture fitness test.

**From Provider Comparison (Wave 3)**: The domain types (`ContentBlock`, `Usage`, `FinishReason`, `ModelCapabilities`) are designed to be identical across all providers. The Copilot adapter produces the same types as Anthropic/OpenAI adapters. The unique complexity (session lifecycle, agent loop suppression, built-in tool exclusion) is entirely contained within the adapter and driver.

The membrane is defined. Build it.

---

*"Make the simple things simple, and the hard things possible." — Larry Wall*

*Applied here: The simple thing is Amplifier consuming uniform domain types. The hard thing is taming an agentic SDK. The adapter makes both possible.*