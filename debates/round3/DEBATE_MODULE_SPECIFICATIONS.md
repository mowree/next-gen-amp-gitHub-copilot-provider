# DEBATE ROUND 3: Concrete Module Specifications

**Author**: Zen Architect  
**Date**: 2026-03-08  
**Status**: Implementation Constitution — Ready for modular-builder  
**Sources**: Round 1 Golden Vision, Round 2 SDK Boundary Design, Round 2 Testing Reconciliation

---

## Preamble: How to Read These Specifications

Each module spec is **self-contained**. An AI agent implementing a module needs only:
1. This specification
2. The shared domain types in `_types.py` (defined in Section 0)
3. The test scaffold in the spec's **Test Specification** section

An agent should be able to regenerate any single module by reading **only** this file plus running the tests. If an agent needs to read more than 3 other files, this spec is incomplete — treat that as a bug in the specification.

**Dependency Rule**: All three modules are **leaf dependencies**. They import from:
- Python stdlib only (`re`, `json`, `uuid`, `dataclasses`, `enum`, `typing`, `asyncio`)
- The shared `_types.py` domain types (defined below)
- `sdk_adapter/` boundary module (for `session_factory.py` only)

They are **never imported by each other**. The dependency DAG is a tree, not a graph.

---

## Section 0: Shared Domain Types (`_types.py`)

These types are the foundation. All three modules depend on them. They contain **zero SDK imports**.

```python
# provider_github_copilot/_types.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContentBlockType(Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"


class FinishReason(Enum):
    STOP = "stop"
    TOOL_USE = "tool_use"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class TextBlock:
    text: str
    type: ContentBlockType = field(default=ContentBlockType.TEXT, init=False)


@dataclass(frozen=True, slots=True)
class ThinkingBlock:
    thinking: str
    signature: str | None = None
    type: ContentBlockType = field(default=ContentBlockType.THINKING, init=False)


@dataclass(frozen=True, slots=True)
class ToolCallBlock:
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    type: ContentBlockType = field(default=ContentBlockType.TOOL_CALL, init=False)


ContentBlock = TextBlock | ThinkingBlock | ToolCallBlock


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    thinking_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class SessionHandle:
    """Opaque reference to an SDK session. Domain code never inspects internals."""
    id: str


@dataclass(frozen=True, slots=True)
class SessionConfig:
    """Domain-level session configuration. Contains zero SDK types."""
    model_id: str
    system_prompt: str | None
    max_output_tokens: int
    tools: list[ToolDefinition]
    temperature: float | None = None
    thinking_budget_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """A tool the model may request. Domain type — not an SDK type."""
    name: str
    description: str
    parameters_schema: dict[str, Any]
```

---

## Module 1: `errors/exceptions.py`

### 1.1 Purpose and Scope

**Single responsibility**: Translate SDK exceptions into domain exceptions with retryability classification.

This module is the **error boundary** of the provider. It defines the complete domain exception hierarchy and provides the `translate_sdk_error()` function that is called at every SDK interaction point. No SDK exception may propagate beyond this module.

**Scope boundaries**:
- IN: Exception class definitions, translation function, retry_after extraction
- OUT: Retry logic, retry decisions, logging, telemetry — those belong to callers
- OUT: SDK imports — the caller passes an `Exception`; this module classifies it by string inspection and `isinstance` checks against lazily-imported SDK types

**File location**: `provider_github_copilot/errors/exceptions.py`  
**Target size**: 200–280 lines  
**Dependencies**: stdlib only (`re`, `typing`), no `_types.py` needed

---

### 1.2 Public Interface

```python
# provider_github_copilot/errors/exceptions.py
from __future__ import annotations

__all__ = [
    "CopilotProviderError",
    "CopilotAuthError",
    "CopilotRateLimitError",
    "CopilotTimeoutError",
    "CopilotContentFilterError",
    "CopilotSessionError",
    "CopilotModelNotFoundError",
    "CopilotSubprocessError",
    "CopilotCircuitBreakerError",
    "translate_sdk_error",
    "is_retryable",
    "extract_retry_after",
]
```

**Exception Hierarchy (complete)**:

```python
class CopilotProviderError(Exception):
    """
    Base error for all Copilot provider failures.

    Every error carries:
    - retryable: Whether the caller may safely retry the operation
    - retry_after: Seconds to wait before retry (None if not specified)
    - original: The original exception that triggered this (for tracing)

    NEVER raise this class directly — use a specific subclass.
    The only correct place to instantiate these is in translate_sdk_error().
    """
    retryable: bool
    retry_after: float | None
    original: Exception | None

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        retry_after: float | None = None,
        original: Exception | None = None,
    ) -> None: ...


class CopilotAuthError(CopilotProviderError):
    """
    Authentication or authorization failure.

    Contract:
    - ALWAYS retryable=False (credentials don't fix themselves)
    - Triggers: 401, 403, invalid token, permission denied

    Caller MUST NOT retry. Caller SHOULD surface to user for credential refresh.
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...


class CopilotRateLimitError(CopilotProviderError):
    """
    Rate limit or quota exceeded.

    Contract:
    - ALWAYS retryable=True
    - retry_after extracted from error metadata or response headers
    - If retry_after is None, caller MUST apply exponential backoff (policy, not mechanism)

    Triggers: 429, quota exceeded, token bucket exhausted
    """
    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        original: Exception | None = None,
    ) -> None: ...


class CopilotTimeoutError(CopilotProviderError):
    """
    Request or connection timed out.

    Contract:
    - ALWAYS retryable=True (timeouts are transient)
    - retry_after is None (caller applies backoff policy)

    Triggers: request timeout, stream timeout, connection timeout
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...


class CopilotContentFilterError(CopilotProviderError):
    """
    Content blocked by safety policy.

    Contract:
    - ALWAYS retryable=False (same input → same block)
    - Caller SHOULD surface to user with explanation

    Triggers: content_filter, safety policy violation
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...


class CopilotSessionError(CopilotProviderError):
    """
    Session creation, management, or destruction failure.

    Contract:
    - ALWAYS retryable=True (session can be recreated)
    - retry_after is None

    Triggers: session creation failed, session destroyed unexpectedly
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...


class CopilotModelNotFoundError(CopilotProviderError):
    """
    Requested model is not available via this provider.

    Contract:
    - ALWAYS retryable=False (model availability doesn't change per-request)
    - Caller SHOULD fall back to a default model (policy decision, not ours)

    Triggers: model_not_found, model_unavailable
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...


class CopilotSubprocessError(CopilotProviderError):
    """
    CLI subprocess crashed or is unreachable.

    Contract:
    - ALWAYS retryable=True (subprocess can be restarted)
    - Callers SHOULD trigger client health check and restart

    Triggers: subprocess exit, JSON-RPC connection lost, process not found
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...


class CopilotCircuitBreakerError(CopilotProviderError):
    """
    Agent loop exceeded safety limits (turn count or timeout).

    Contract:
    - ALWAYS retryable=False (circuit is tripped; same request → same result)
    - Caller MUST NOT retry without human intervention or request modification

    Triggers: turn count > 10, loop timeout, recursive agent detection
    """
    def __init__(self, message: str, *, original: Exception | None = None) -> None: ...
```

**Translation Function**:

```python
def translate_sdk_error(exc: Exception) -> CopilotProviderError:
    """
    Translate ANY exception (SDK or otherwise) to a domain exception.

    This is the sole error boundary for the SDK adapter. It MUST be called
    in every except block that catches SDK exceptions.

    Classification strategy:
    1. Try isinstance() checks against SDK exception classes (if importable)
    2. Fall back to string/attribute inspection for resilience
    3. Catch-all: CopilotProviderError(retryable=False)

    Args:
        exc: Any exception — SDK exception, stdlib exception, or unknown

    Returns:
        A CopilotProviderError subclass. NEVER raises.

    Contract:
    - MUST NOT raise any exception itself
    - MUST preserve original exception as .original attribute
    - MUST set retryable correctly per the classification table
    - MUST extract retry_after from rate limit errors when present

    Example:
        try:
            await sdk_client.create_session(config)
        except Exception as exc:
            raise translate_sdk_error(exc) from exc
    """
    ...


def is_retryable(exc: Exception) -> bool:
    """
    Return True if the exception indicates a retryable condition.

    Works for both CopilotProviderError subclasses (reads .retryable)
    and unknown exceptions (conservative: returns False).

    Args:
        exc: Any exception

    Returns:
        True if safe to retry, False otherwise

    Example:
        if is_retryable(exc):
            await asyncio.sleep(backoff)
            return await retry_operation()
    """
    ...


def extract_retry_after(exc: Exception) -> float | None:
    """
    Extract the retry_after duration in seconds from an exception.

    Sources checked in order:
    1. exc.retry_after attribute (CopilotRateLimitError or SDK error)
    2. Retry-After header embedded in error message (regex extraction)
    3. None if not found

    Args:
        exc: Any exception, typically CopilotRateLimitError

    Returns:
        Seconds to wait before retry, or None if not specified

    Example:
        retry_after = extract_retry_after(exc)
        delay = retry_after if retry_after is not None else default_backoff
        await asyncio.sleep(delay)
    """
    ...
```

---

### 1.3 Internal Implementation Contract

**`translate_sdk_error()` Classification Table** (implementation must match exactly):

```
INPUT EXCEPTION CLASS/PATTERN          → OUTPUT CLASS              RETRYABLE
─────────────────────────────────────────────────────────────────────────────
SDK AuthenticationError                → CopilotAuthError          False
SDK InvalidTokenError                  → CopilotAuthError          False
SDK PermissionDeniedError              → CopilotAuthError          False
"401" in str(exc) or "403" in str(exc) → CopilotAuthError          False
SDK RateLimitError                     → CopilotRateLimitError     True, extract retry_after
SDK QuotaExceededError                 → CopilotRateLimitError     True, extract retry_after
"429" in str(exc)                      → CopilotRateLimitError     True, extract from message
SDK TimeoutError                       → CopilotTimeoutError       True
SDK RequestTimeoutError                → CopilotTimeoutError       True
asyncio.TimeoutError                   → CopilotTimeoutError       True
SDK ContentFilterError                 → CopilotContentFilterError False
SDK SafetyError                        → CopilotContentFilterError False
SDK ModelNotFoundError                 → CopilotModelNotFoundError False
SDK ModelUnavailableError              → CopilotModelNotFoundError False
SDK SessionCreateError                 → CopilotSessionError       True
SDK SessionDestroyError                → CopilotSessionError       True
SDK ConnectionError                    → CopilotSubprocessError    True
SDK ProcessExitedError                 → CopilotSubprocessError    True
ConnectionRefusedError (stdlib)        → CopilotSubprocessError    True
SDK InternalError                      → CopilotProviderError      True
Everything else                        → CopilotProviderError      False
```

**`extract_retry_after()` Regex Pattern**:

```python
_RETRY_AFTER_PATTERN = re.compile(
    r"retry.after\D*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
```

**SDK Import Strategy** (resilient to SDK absence):

```python
# Try to import SDK error types. If SDK is not installed, fall back
# to string/attribute inspection only.
try:
    from copilot_sdk import (
        AuthenticationError as _SdkAuthError,
        RateLimitError as _SdkRateLimitError,
        # ... etc
    )
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    _SdkAuthError = None  # type: ignore[assignment]
    # ... etc
```

---

### 1.4 Test Specification

**File**: `tests/unit/test_error_translation.py`  
**Marker**: `@pytest.mark.pure` (all tests, <10ms each)

```python
"""
Tests for errors/exceptions.py

Contract: Every SDK exception type maps to exactly one domain exception with
correct retryability. translate_sdk_error() MUST NEVER raise.
"""
import pytest
from provider_github_copilot.errors.exceptions import (
    CopilotAuthError,
    CopilotRateLimitError,
    CopilotTimeoutError,
    CopilotContentFilterError,
    CopilotSessionError,
    CopilotModelNotFoundError,
    CopilotSubprocessError,
    CopilotProviderError,
    translate_sdk_error,
    is_retryable,
    extract_retry_after,
)


class TestExceptionHierarchy:
    """Contract: All domain errors are CopilotProviderError subclasses."""

    @pytest.mark.pure
    def test_all_errors_inherit_from_base(self):
        errors = [
            CopilotAuthError("x"),
            CopilotRateLimitError("x"),
            CopilotTimeoutError("x"),
            CopilotContentFilterError("x"),
            CopilotSessionError("x"),
            CopilotModelNotFoundError("x"),
            CopilotSubprocessError("x"),
        ]
        for err in errors:
            assert isinstance(err, CopilotProviderError), (
                f"{type(err).__name__} must inherit from CopilotProviderError"
            )

    @pytest.mark.pure
    def test_auth_error_is_never_retryable(self):
        """Contract: CopilotAuthError.retryable MUST be False."""
        err = CopilotAuthError("credentials invalid")
        assert err.retryable is False, (
            "Contract violation: CopilotAuthError MUST be retryable=False. "
            "Credentials do not fix themselves between retries."
        )

    @pytest.mark.pure
    def test_rate_limit_error_is_always_retryable(self):
        """Contract: CopilotRateLimitError.retryable MUST be True."""
        err = CopilotRateLimitError("rate limited")
        assert err.retryable is True, (
            "Contract violation: CopilotRateLimitError MUST be retryable=True."
        )

    @pytest.mark.pure
    def test_timeout_error_is_always_retryable(self):
        """Contract: CopilotTimeoutError.retryable MUST be True."""
        err = CopilotTimeoutError("timed out")
        assert err.retryable is True

    @pytest.mark.pure
    def test_content_filter_error_is_never_retryable(self):
        """Contract: CopilotContentFilterError.retryable MUST be False."""
        err = CopilotContentFilterError("blocked")
        assert err.retryable is False

    @pytest.mark.pure
    def test_circuit_breaker_is_never_retryable(self):
        from provider_github_copilot.errors.exceptions import CopilotCircuitBreakerError
        err = CopilotCircuitBreakerError("turn limit exceeded")
        assert err.retryable is False

    @pytest.mark.pure
    def test_original_exception_is_preserved(self):
        """Contract: .original MUST reference the causing exception."""
        cause = ValueError("sdk internal failure")
        err = CopilotProviderError("wrapped", original=cause)
        assert err.original is cause


class TestTranslateSdkError:
    """Contract: translate_sdk_error() translates ALL exceptions correctly."""

    @pytest.mark.pure
    def test_never_raises_for_any_input(self):
        """Contract: translate_sdk_error() MUST NEVER raise."""
        inputs = [
            ValueError("random"),
            RuntimeError("subprocess"),
            KeyError("missing"),
            Exception("base"),
            None.__class__("absurd"),  # type: ignore
        ]
        for exc in inputs:
            result = translate_sdk_error(exc)  # Must not raise
            assert isinstance(result, CopilotProviderError)

    @pytest.mark.pure
    def test_asyncio_timeout_maps_to_timeout_error(self):
        """Contract: stdlib asyncio.TimeoutError → CopilotTimeoutError."""
        import asyncio
        result = translate_sdk_error(asyncio.TimeoutError())
        assert isinstance(result, CopilotTimeoutError), (
            "Contract violation: asyncio.TimeoutError must map to CopilotTimeoutError, "
            f"got {type(result).__name__}"
        )
        assert result.retryable is True

    @pytest.mark.pure
    def test_connection_refused_maps_to_subprocess_error(self):
        """Contract: ConnectionRefusedError → CopilotSubprocessError."""
        result = translate_sdk_error(ConnectionRefusedError("connection refused"))
        assert isinstance(result, CopilotSubprocessError)
        assert result.retryable is True

    @pytest.mark.pure
    def test_unknown_exception_maps_to_base_non_retryable(self):
        """Contract: Unknown exceptions → CopilotProviderError(retryable=False)."""
        result = translate_sdk_error(ZeroDivisionError("what?"))
        assert type(result) is CopilotProviderError
        assert result.retryable is False

    @pytest.mark.pure
    def test_original_always_preserved(self):
        """Contract: translate_sdk_error MUST set .original on every result."""
        exc = ValueError("test")
        result = translate_sdk_error(exc)
        assert result.original is exc

    @pytest.mark.pure
    def test_string_based_401_detection(self):
        """Contract: '401' in message → CopilotAuthError even without SDK types."""
        result = translate_sdk_error(RuntimeError("HTTP 401 unauthorized"))
        assert isinstance(result, CopilotAuthError)
        assert result.retryable is False

    @pytest.mark.pure
    def test_string_based_429_detection(self):
        """Contract: '429' in message → CopilotRateLimitError even without SDK types."""
        result = translate_sdk_error(RuntimeError("HTTP 429 too many requests"))
        assert isinstance(result, CopilotRateLimitError)
        assert result.retryable is True


class TestExtractRetryAfter:
    """Contract: retry_after extraction from error metadata."""

    @pytest.mark.pure
    def test_extracts_from_rate_limit_error_attribute(self):
        """Contract: CopilotRateLimitError.retry_after is returned directly."""
        err = CopilotRateLimitError("limited", retry_after=30.0)
        assert extract_retry_after(err) == 30.0

    @pytest.mark.pure
    def test_extracts_from_error_message_regex(self):
        """Contract: 'retry after 60' in message → 60.0."""
        err = RuntimeError("Rate limited: retry after 60 seconds")
        assert extract_retry_after(err) == 60.0

    @pytest.mark.pure
    def test_returns_none_when_not_present(self):
        """Contract: Returns None when retry_after is not available."""
        err = CopilotTimeoutError("timed out")
        assert extract_retry_after(err) is None

    @pytest.mark.pure
    def test_handles_decimal_retry_after(self):
        """Contract: Decimal retry_after values are supported."""
        err = RuntimeError("retry after 1.5 seconds")
        result = extract_retry_after(err)
        assert result == 1.5


class TestIsRetryable:
    """Contract: is_retryable() reads .retryable attribute correctly."""

    @pytest.mark.pure
    def test_true_for_retryable_domain_error(self):
        assert is_retryable(CopilotTimeoutError("timeout")) is True

    @pytest.mark.pure
    def test_false_for_non_retryable_domain_error(self):
        assert is_retryable(CopilotAuthError("auth")) is False

    @pytest.mark.pure
    def test_false_for_unknown_exception(self):
        """Contract: Unknown exceptions are conservatively non-retryable."""
        assert is_retryable(ValueError("unknown")) is False
```

---

### 1.5 Success Criteria

- [ ] All 22+ unit tests pass
- [ ] `translate_sdk_error()` never raises for any input (fuzz tested with 1000 random exceptions)
- [ ] Every `CopilotProviderError` subclass has correct `retryable` default
- [ ] SDK import failure is graceful (module works without SDK installed)
- [ ] Module is ≤280 lines
- [ ] Zero imports from outside stdlib and this file itself
- [ ] `pyright --strict` reports zero errors on this file

---

## Module 2: `converters/tool_parsing.py`

### 2.1 Purpose and Scope

**Single responsibility**: Parse tool calls from streaming events and assembled `ChatResponse` content, providing a clean `parse_tool_calls()` implementation for the Provider protocol.

This module handles **two distinct parsing paths**:

1. **From `ChatResponse`**: Extract `ToolCallBlock` objects from an already-assembled response. This is the primary path — the `complete()` function calls `parse_tool_calls()` after streaming.
2. **From streaming events**: Accumulate partial tool call JSON across multiple streaming deltas into complete `ToolCallBlock` objects. This is used by the stream accumulator.

**Scope boundaries**:
- IN: JSON parsing, tool call extraction, argument validation, partial JSON accumulation
- OUT: Schema validation of tool arguments (caller's responsibility), tool execution (NEVER), preToolUse deny hook (belongs in sdk_driver)
- OUT: Tool routing, tool result handling — Amplifier orchestrator owns those

**File location**: `provider_github_copilot/converters/tool_parsing.py`  
**Target size**: 200–280 lines  
**Dependencies**: stdlib (`json`, `re`, `typing`), `_types.py` only

---

### 2.2 Public Interface

```python
# provider_github_copilot/converters/tool_parsing.py
from __future__ import annotations

__all__ = [
    "parse_tool_calls",
    "ToolCallAccumulator",
    "ToolCallParseError",
]
```

**Primary Function**:

```python
def parse_tool_calls(content: list[ContentBlock]) -> list[ToolCallBlock]:
    """
    Extract all tool call blocks from a list of content blocks.

    This is the implementation of the Provider protocol's parse_tool_calls()
    method. It filters and returns only ToolCallBlock items from the content.

    Args:
        content: List of ContentBlock (TextBlock | ThinkingBlock | ToolCallBlock)

    Returns:
        List of ToolCallBlock objects, in the order they appear in content.
        Returns empty list if no tool calls are present.

    Contract:
    - MUST NOT mutate the input list
    - MUST preserve order of tool calls as they appear in content
    - MUST return empty list (not None) when no tool calls present
    - MUST NOT raise for any valid ContentBlock input

    Example:
        response = await provider.complete(request)
        tool_calls = parse_tool_calls(response.content)
        for call in tool_calls:
            result = await execute_tool(call.tool_name, call.arguments)
    """
    ...
```

**Streaming Accumulator**:

```python
class ToolCallAccumulator:
    """
    Accumulates streaming tool call deltas into complete ToolCallBlock objects.

    The Copilot SDK streams tool calls across multiple events:
    - tool_use_start: Provides tool_call_id and tool_name
    - tool_use_delta: Provides partial arguments JSON string
    - tool_use_complete: Signals the tool call is fully received

    This class is stateful and NOT thread-safe. One instance per streaming session.

    State machine:
        IDLE → (on_start called) → ACCUMULATING → (on_complete called) → IDLE
        ACCUMULATING → (on_start called with new id) → ACCUMULATING (implicit complete)

    Example:
        accumulator = ToolCallAccumulator()
        for event in sdk_events:
            if event.type == "tool_use_start":
                accumulator.on_start(event.data.id, event.data.name)
            elif event.type == "tool_use_delta":
                accumulator.on_delta(event.data.delta)
            elif event.type == "tool_use_complete":
                tool_call = accumulator.on_complete()
                if tool_call:
                    captured_tools.append(tool_call)
    """

    def on_start(self, tool_call_id: str, tool_name: str) -> None:
        """
        Begin accumulating a new tool call.

        If a previous tool call was in progress (no on_complete called),
        it is discarded. This handles malformed SDK streams gracefully.

        Args:
            tool_call_id: Unique identifier for this tool call (from SDK)
            tool_name: Name of the tool being called (from SDK)

        Contract:
        - MUST reset any in-progress accumulation
        - MUST NOT raise
        """
        ...

    def on_delta(self, arguments_fragment: str) -> None:
        """
        Append a fragment to the arguments JSON being accumulated.

        If no tool call is in progress (on_start not called), this is a no-op.
        This handles out-of-order SDK events gracefully.

        Args:
            arguments_fragment: A partial JSON string for the tool arguments

        Contract:
        - MUST be a no-op if called before on_start
        - MUST NOT raise for any string input, including malformed JSON fragments
        """
        ...

    def on_complete(self) -> ToolCallBlock | None:
        """
        Finalize the current tool call and return a complete ToolCallBlock.

        Parses the accumulated arguments JSON. If parsing fails, falls back
        to an empty dict (tool call captured but arguments lost).

        Returns:
            Complete ToolCallBlock if a tool call was in progress, None otherwise.

        Contract:
        - MUST return None if on_start was never called
        - MUST return a valid ToolCallBlock even if argument JSON is malformed
          (use empty dict as fallback — never raise)
        - MUST reset internal state after returning
        - MUST NOT raise

        Example:
            tool_call = accumulator.on_complete()
            # tool_call.arguments will be {} if JSON was malformed
        """
        ...

    def is_accumulating(self) -> bool:
        """
        Return True if a tool call accumulation is in progress.

        Used by the stream processor to detect incomplete tool calls
        at stream end (which indicates a malformed stream).

        Returns:
            True if on_start was called but on_complete has not yet been called.
        """
        ...

    def reset(self) -> None:
        """
        Discard any in-progress accumulation and return to idle state.

        Called when the stream ends abnormally or when a new session starts.

        Contract:
        - MUST be safe to call in any state
        - MUST NOT raise
        """
        ...
```

**Error Type**:

```python
class ToolCallParseError(ValueError):
    """
    Raised when tool call content is structurally invalid in a way that
    cannot be recovered from gracefully.

    This is NOT raised by parse_tool_calls() or ToolCallAccumulator —
    those always return partial results. It is available for callers
    that want to signal hard parse failures in their own code.

    Attributes:
        raw_arguments: The raw JSON string that failed to parse
        tool_name: The tool name associated with the failure
    """
    raw_arguments: str
    tool_name: str

    def __init__(
        self, message: str, *, raw_arguments: str, tool_name: str
    ) -> None: ...
```

---

### 2.3 Internal Implementation Contract

**`parse_tool_calls()` implementation**:

```python
def parse_tool_calls(content: list[ContentBlock]) -> list[ToolCallBlock]:
    # Filter-only implementation. No transformation needed.
    # ToolCallBlock objects are already fully constructed by the time
    # they appear in content (the accumulator handles parsing).
    return [block for block in content if isinstance(block, ToolCallBlock)]
```

This is intentionally trivial. The complexity lives in `ToolCallAccumulator`.

**`ToolCallAccumulator` internal state**:

```python
@dataclass
class _PendingToolCall:
    tool_call_id: str
    tool_name: str
    arguments_json: str = ""  # Accumulated fragments
```

**JSON parse fallback strategy**:

```python
def _parse_arguments(raw_json: str, tool_name: str) -> dict[str, Any]:
    """
    Parse tool arguments with graceful fallback.

    Attempt order:
    1. Direct json.loads(raw_json)
    2. json.loads("{}") if raw_json is empty
    3. Return {} if json.loads fails (malformed JSON)

    NEVER raises. Always returns a dict.
    """
    if not raw_json.strip():
        return {}
    try:
        result = json.loads(raw_json)
        if isinstance(result, dict):
            return result
        # SDK sent non-object JSON (array, string, etc.) — treat as empty
        return {}
    except json.JSONDecodeError:
        # Malformed JSON — log at WARNING level and return empty dict
        # Tool call is captured; arguments are lost. Caller will see empty args.
        return {}
```

---

### 2.4 Test Specification

**File**: `tests/unit/test_tool_parsing.py`  
**Marker**: `@pytest.mark.pure` (all tests, <10ms each)

```python
"""
Tests for converters/tool_parsing.py

Contract: parse_tool_calls() extracts ToolCallBlock objects from content.
ToolCallAccumulator assembles complete tool calls from streaming deltas.
Neither function EVER raises for any valid input.
"""
import pytest
from provider_github_copilot._types import TextBlock, ThinkingBlock, ToolCallBlock
from provider_github_copilot.converters.tool_parsing import (
    parse_tool_calls,
    ToolCallAccumulator,
)


class TestParseToolCalls:
    """Contract: parse_tool_calls() extracts ToolCallBlock from content list."""

    @pytest.mark.pure
    def test_returns_empty_list_for_empty_content(self):
        """Contract: Returns [] not None for empty input."""
        result = parse_tool_calls([])
        assert result == []

    @pytest.mark.pure
    def test_returns_empty_list_for_text_only_content(self):
        """Contract: Returns [] when no ToolCallBlock present."""
        content = [TextBlock(text="Hello world")]
        result = parse_tool_calls(content)
        assert result == []

    @pytest.mark.pure
    def test_extracts_single_tool_call(self):
        """Contract: Returns [ToolCallBlock] when one tool call present."""
        tool = ToolCallBlock(
            tool_call_id="call_abc",
            tool_name="read_file",
            arguments={"path": "/tmp/test.py"},
        )
        content = [TextBlock(text="I'll read it"), tool]
        result = parse_tool_calls(content)
        assert result == [tool]

    @pytest.mark.pure
    def test_extracts_multiple_tool_calls_in_order(self):
        """Contract: Multiple tool calls returned in content order."""
        tool1 = ToolCallBlock(tool_call_id="1", tool_name="read_file", arguments={})
        tool2 = ToolCallBlock(tool_call_id="2", tool_name="write_file", arguments={})
        content = [tool1, TextBlock(text="between"), tool2]
        result = parse_tool_calls(content)
        assert result == [tool1, tool2]

    @pytest.mark.pure
    def test_does_not_mutate_input(self):
        """Contract: Input list is not modified."""
        tool = ToolCallBlock(tool_call_id="1", tool_name="x", arguments={})
        content = [tool]
        original_len = len(content)
        parse_tool_calls(content)
        assert len(content) == original_len

    @pytest.mark.pure
    def test_ignores_thinking_blocks(self):
        """Contract: ThinkingBlock is not included in output."""
        content = [
            ThinkingBlock(thinking="Let me think...", signature="sig123"),
            ToolCallBlock(tool_call_id="1", tool_name="x", arguments={}),
        ]
        result = parse_tool_calls(content)
        assert len(result) == 1
        assert result[0].tool_name == "x"


class TestToolCallAccumulator:
    """Contract: Streaming accumulator assembles complete tool calls from deltas."""

    @pytest.mark.pure
    def test_complete_returns_none_before_any_start(self):
        """Contract: on_complete() returns None if no tool call started."""
        acc = ToolCallAccumulator()
        result = acc.on_complete()
        assert result is None

    @pytest.mark.pure
    def test_is_accumulating_false_before_start(self):
        acc = ToolCallAccumulator()
        assert acc.is_accumulating() is False

    @pytest.mark.pure
    def test_is_accumulating_true_after_start(self):
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "read_file")
        assert acc.is_accumulating() is True

    @pytest.mark.pure
    def test_is_accumulating_false_after_complete(self):
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "read_file")
        acc.on_complete()
        assert acc.is_accumulating() is False

    @pytest.mark.pure
    def test_single_delta_produces_correct_tool_call(self):
        """Contract: Full JSON in single delta is parsed correctly."""
        acc = ToolCallAccumulator()
        acc.on_start("call_xyz", "bash")
        acc.on_delta('{"command": "ls -la"}')
        result = acc.on_complete()

        assert result is not None
        assert result.tool_call_id == "call_xyz"
        assert result.tool_name == "bash"
        assert result.arguments == {"command": "ls -la"}

    @pytest.mark.pure
    def test_multiple_deltas_are_concatenated(self):
        """Contract: Multiple deltas build one complete JSON string."""
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "search")
        acc.on_delta('{"query":')
        acc.on_delta(' "hello world"')
        acc.on_delta("}")
        result = acc.on_complete()

        assert result is not None
        assert result.arguments == {"query": "hello world"}

    @pytest.mark.pure
    def test_empty_arguments_produces_empty_dict(self):
        """Contract: Empty argument stream → {} not None or error."""
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "no_args_tool")
        result = acc.on_complete()

        assert result is not None
        assert result.arguments == {}

    @pytest.mark.pure
    def test_malformed_json_produces_empty_dict(self):
        """Contract: Malformed JSON → {} (never raises)."""
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "broken_tool")
        acc.on_delta('{"incomplete": ')  # Truncated JSON
        result = acc.on_complete()

        assert result is not None, "Must return ToolCallBlock even for malformed JSON"
        assert result.arguments == {}, (
            "Contract violation: malformed JSON MUST produce empty dict, not raise. "
            "Tool call is captured; arguments are lost gracefully."
        )

    @pytest.mark.pure
    def test_delta_before_start_is_ignored(self):
        """Contract: on_delta() before on_start() is a no-op."""
        acc = ToolCallAccumulator()
        acc.on_delta('{"this": "is dropped"}')  # Must not raise
        assert acc.is_accumulating() is False

    @pytest.mark.pure
    def test_second_start_discards_first(self):
        """Contract: New on_start() discards in-progress accumulation."""
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "first_tool")
        acc.on_delta('{"partial":')

        # New tool call starts — first is discarded
        acc.on_start("call_2", "second_tool")
        acc.on_delta('{"complete": true}')
        result = acc.on_complete()

        assert result is not None
        assert result.tool_call_id == "call_2"
        assert result.tool_name == "second_tool"

    @pytest.mark.pure
    def test_reset_returns_to_idle(self):
        """Contract: reset() is always safe and returns to idle."""
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "tool")
        acc.on_delta('{"x": 1}')
        acc.reset()
        assert acc.is_accumulating() is False
        assert acc.on_complete() is None

    @pytest.mark.pure
    def test_non_object_json_produces_empty_dict(self):
        """Contract: Non-object valid JSON (array, string) → {} fallback."""
        acc = ToolCallAccumulator()
        acc.on_start("call_1", "tool")
        acc.on_delta('["not", "an", "object"]')
        result = acc.on_complete()

        assert result is not None
        assert result.arguments == {}
```

**Property-Based Tests** (`tests/property/test_tool_parsing_properties.py`):

```python
from hypothesis import given, strategies as st
import pytest

@pytest.mark.pure
class TestToolParsingProperties:

    @given(st.text())
    def test_accumulator_on_delta_never_raises(self, fragment: str):
        """Property: on_delta() never raises for any string input."""
        acc = ToolCallAccumulator()
        acc.on_start("id", "tool")
        acc.on_delta(fragment)  # Must not raise

    @given(st.text())
    def test_accumulator_on_complete_never_raises(self, fragment: str):
        """Property: on_complete() never raises after any delta sequence."""
        acc = ToolCallAccumulator()
        acc.on_start("id", "tool")
        acc.on_delta(fragment)
        result = acc.on_complete()  # Must not raise
        assert result is not None
        assert isinstance(result.arguments, dict)

    @given(st.lists(st.builds(
        ToolCallBlock,
        tool_call_id=st.text(min_size=1, max_size=50),
        tool_name=st.text(min_size=1, max_size=50),
        arguments=st.dictionaries(st.text(), st.text()),
    )))
    def test_parse_preserves_count(self, tool_calls: list[ToolCallBlock]):
        """Property: parse_tool_calls() count matches input ToolCallBlock count."""
        content = tool_calls  # All are ToolCallBlock
        result = parse_tool_calls(content)
        assert len(result) == len(tool_calls)
```

---

### 2.5 Success Criteria

- [ ] All unit tests pass
- [ ] All property tests pass with 100+ examples each
- [ ] `parse_tool_calls([])` returns `[]` (not `None`)
- [ ] `ToolCallAccumulator.on_complete()` never raises for any input
- [ ] Malformed JSON accumulation returns `ToolCallBlock(arguments={})` not exception
- [ ] Module is ≤280 lines
- [ ] Zero imports from outside stdlib + `_types.py`
- [ ] `pyright --strict` reports zero errors

---

## Module 3: `client/session_factory.py`

### 3.1 Purpose and Scope

**Single responsibility**: Create and destroy ephemeral SDK sessions that implement the Deny + Destroy pattern for Amplifier sovereignty.

This is the **session lifecycle** module. It creates ephemeral Copilot SDK sessions with the preToolUse deny hook pre-installed, and destroys them immediately after each completion. It is the concrete realization of the core architectural commitment: **the SDK never accumulates conversation state**.

**The Deny + Destroy Pattern** (this module's entire raison d'être):
1. **Deny**: Install `preToolUse` hook that always returns DENY — the SDK never executes tools
2. **Destroy**: Destroy the session immediately after the first turn completes — the SDK never accumulates state

**Scope boundaries**:
- IN: Session creation with preToolUse deny hook, session destruction, session config translation
- OUT: Tool execution (always denied), state accumulation (ephemeral sessions only), retry logic (callers own that), circuit breaking (belongs in `sdk_driver/loop_controller.py`)
- OUT: Connection/client lifecycle — that belongs in `client/wrapper.py`

**File location**: `provider_github_copilot/client/session_factory.py`  
**Target size**: 200–300 lines  
**Dependencies**: stdlib (`uuid`, `typing`, `asyncio`), `_types.py`, `errors/exceptions.py`

**Critical**: This module IS the only module that installs the `preToolUse` deny hook. If this hook is not installed on every session, Amplifier sovereignty is violated.

---

### 3.2 Public Interface

```python
# provider_github_copilot/client/session_factory.py
from __future__ import annotations

__all__ = [
    "SessionFactory",
    "SessionFactoryProtocol",
    "EphemeralSession",
]
```

**Protocol (Testability Contract)**:

```python
class SessionFactoryProtocol(Protocol):
    """
    Interface for session lifecycle management.

    This protocol enables test doubles. The CopilotSessionFactory implements
    this; tests provide a FakeSessionFactory.
    """

    async def create_session(
        self,
        config: SessionConfig,
    ) -> EphemeralSession:
        """
        Create a new ephemeral SDK session configured for Amplifier sovereignty.

        Implementations MUST:
        1. Install the preToolUse deny hook on every session
        2. Configure the session as ephemeral (no state accumulation)
        3. Wrap any SDK exception in CopilotSessionError
        4. Return an EphemeralSession handle — NOT a raw SDK session

        Args:
            config: Domain-level session configuration (zero SDK types)

        Returns:
            EphemeralSession with the SDK session handle wrapped

        Raises:
            CopilotSessionError: If session creation fails (always retryable)
            CopilotAuthError: If credentials are invalid (never retryable)

        Contract:
        - MUST install preToolUse deny hook before returning
        - MUST NOT return None
        - MUST wrap all SDK exceptions via translate_sdk_error()
        """
        ...

    async def destroy_session(self, session: EphemeralSession) -> None:
        """
        Destroy a session, releasing SDK resources.

        Implementations MUST:
        1. Call SDK session destroy/disconnect
        2. Clean up any internal state for this session
        3. Silently swallow errors — destruction MUST NOT raise

        Args:
            session: The session to destroy

        Contract:
        - MUST be safe to call on an already-destroyed session (idempotent)
        - MUST NOT raise under any circumstances (log errors, swallow them)
        - MUST release all SDK resources associated with the session
        """
        ...
```

**Session Handle Type**:

```python
@dataclass(frozen=True, slots=True)
class EphemeralSession:
    """
    Opaque handle to a live SDK session.

    This is the domain-level representation of a session. Domain code (the
    provider orchestrator, stream accumulator, etc.) operates on this type.
    The actual SDK session object is stored in the factory's internal map.

    Attributes:
        id: Unique identifier for this session (UUID, not an SDK identifier)
        model_id: The model this session was created with
        created_at_ns: Creation timestamp in nanoseconds (for timeout tracking)
    """
    id: str
    model_id: str
    created_at_ns: int
```

**Concrete Implementation**:

```python
class CopilotSessionFactory:
    """
    Creates and destroys ephemeral SDK sessions with preToolUse deny hook.

    This is the only class in the codebase that imports from the Copilot SDK
    session management APIs. All SDK session objects are stored internally
    and never exposed to domain code.

    Implements SessionFactoryProtocol.

    The preToolUse deny hook is the mechanism that ensures Amplifier's tool
    execution sovereignty. It is installed on every session, without exception.
    If this hook is not installed, the SDK will execute tools autonomously,
    bypassing Amplifier's safety gates, approval workflows, and tool dispatch.

    Usage:
        factory = CopilotSessionFactory(sdk_client=client)

        # Create session (hook is pre-installed)
        session = await factory.create_session(config)

        # Use session via sdk_driver
        async for event in sdk_driver.send_message(session, prompt):
            ...

        # Destroy immediately after use (Deny + Destroy)
        await factory.destroy_session(session)

    Context manager usage (preferred):
        async with factory.session(config) as session:
            async for event in sdk_driver.send_message(session, prompt):
                ...
        # Session is automatically destroyed on exit, even on exception
    """

    def __init__(self, sdk_client: Any) -> None:
        """
        Args:
            sdk_client: The raw SDK client (CopilotClient or equivalent).
                        Type is Any to avoid SDK type imports in this signature.
        """
        ...

    async def create_session(self, config: SessionConfig) -> EphemeralSession:
        """
        Create an ephemeral SDK session with preToolUse deny hook installed.

        Internal steps:
        1. Translate SessionConfig to SDK session config (reverse translation)
        2. Configure preToolUse hook that always returns DENY
        3. Create SDK session
        4. Store SDK session in internal map keyed by EphemeralSession.id
        5. Return EphemeralSession handle

        The preToolUse deny hook:
            async def _deny_all_tools(tool_use):
                return "deny"  # or SDK-appropriate deny response
            sdk_config.hooks.preToolUse = _deny_all_tools

        Args:
            config: Domain session config

        Returns:
            EphemeralSession handle

        Raises:
            CopilotSessionError: Wraps any SDK session creation error
            CopilotAuthError: Wraps SDK authentication errors

        Contract:
        - MUST install preToolUse deny hook before creating session
        - MUST store SDK session in internal map
        - MUST generate UUID for session id (not SDK's session id)
        - MUST record created_at_ns for timeout tracking
        """
        ...

    async def destroy_session(self, session: EphemeralSession) -> None:
        """
        Destroy the SDK session and remove from internal map.

        Internal steps:
        1. Look up SDK session from internal map
        2. Call SDK session.destroy() or equivalent
        3. Remove from internal map
        4. Log any errors but never re-raise

        Args:
            session: The session handle returned by create_session()

        Contract:
        - MUST NOT raise under any circumstances
        - MUST be idempotent (safe for already-destroyed sessions)
        - MUST log warnings for unexpected SDK errors during destruction
        """
        ...

    def session(self, config: SessionConfig) -> _EphemeralSessionContext:
        """
        Context manager that creates and auto-destroys a session.

        Preferred over manual create/destroy to ensure destruction even
        when exceptions occur.

        Usage:
            async with factory.session(config) as session:
                # session is live here
                await do_work(session)
            # session is destroyed here, even if do_work() raised

        Returns:
            Async context manager yielding EphemeralSession
        """
        ...

    def active_session_count(self) -> int:
        """
        Return number of currently active sessions.

        Used by health checks and tests. Should be 0 between requests
        (ephemeral sessions are create-use-destroy per request).
        """
        ...
```

**Context Manager Helper** (internal, not exported):

```python
class _EphemeralSessionContext:
    """
    Async context manager returned by CopilotSessionFactory.session().
    Not part of the public API — use factory.session() directly.
    """

    def __init__(self, factory: CopilotSessionFactory, config: SessionConfig) -> None: ...

    async def __aenter__(self) -> EphemeralSession: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        # MUST destroy session even when exc_type is not None
        ...
```

---

### 3.3 Internal Implementation Contract

**Deny Hook Implementation**:

```python
# This exact pattern MUST be used. The hook's return value depends on
# the SDK version — verify via SDK assumption test.

async def _preToolUse_deny(tool_use_event: Any) -> Any:
    """
    Always deny tool execution. This hook is installed on every session.

    The return value format varies by SDK version:
    - v0.1.x: return {"behavior": "deny"}
    - v0.2.x: return HookResult.deny()
    - Fallback: return "deny"

    The SDK assumption test (tests/sdk_assumptions/test_hooks.py) verifies
    which format the current SDK version expects.
    """
    # Implementation defers to sdk_adapter for version-specific response
    ...
```

**Session Config Translation** (reverse translation — our types → SDK types):

```python
def _to_sdk_config(config: SessionConfig) -> Any:
    """
    Translate SessionConfig to SDK session configuration.
    This reverse-translation lives only inside the factory.
    The exact SDK config type is not imported in this function's signature.
    """
    # Translate fields:
    # config.model_id → sdk_config.model
    # config.system_prompt → sdk_config.system_prompt (if not None)
    # config.max_output_tokens → sdk_config.max_tokens
    # config.temperature → sdk_config.temperature (if not None)
    # config.tools → [_to_sdk_tool(t) for t in config.tools]
    # PLUS: install preToolUse deny hook
    ...
```

**Internal Session Map**:

```python
# Internal state — never exposed
_sessions: dict[str, Any]  # session_id → SDK session object
```

**Error wrapping at every boundary**:

```python
async def create_session(self, config: SessionConfig) -> EphemeralSession:
    try:
        sdk_config = self._to_sdk_config(config)
        sdk_session = await self._sdk_client.create_session(sdk_config)
        session_id = str(uuid4())
        self._sessions[session_id] = sdk_session
        return EphemeralSession(
            id=session_id,
            model_id=config.model_id,
            created_at_ns=time.monotonic_ns(),
        )
    except Exception as exc:
        raise translate_sdk_error(exc) from exc
```

---

### 3.4 Test Specification

**File**: `tests/unit/test_session_factory.py`  
**Markers**: `@pytest.mark.pure` for sync tests, `@pytest.mark.stubbed` for async tests

```python
"""
Tests for client/session_factory.py

Contract: CopilotSessionFactory creates ephemeral sessions with preToolUse deny hook
installed on every session. Sessions are destroyed immediately after use.
The deny hook is NEVER optional.

Critical invariant: If preToolUse deny hook is not installed,
Amplifier's tool sovereignty is violated.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, call
from provider_github_copilot.client.session_factory import (
    CopilotSessionFactory,
    EphemeralSession,
)
from provider_github_copilot._types import SessionConfig, ToolDefinition
from provider_github_copilot.errors.exceptions import (
    CopilotSessionError,
    CopilotAuthError,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_sdk_client():
    """Stub SDK client that records what sessions were created with."""
    client = MagicMock()
    client.create_session = AsyncMock(return_value=MagicMock(
        destroy=AsyncMock(),
        id="sdk_session_123",
    ))
    return client


@pytest.fixture
def factory(mock_sdk_client):
    return CopilotSessionFactory(sdk_client=mock_sdk_client)


@pytest.fixture
def basic_config():
    return SessionConfig(
        model_id="claude-opus-4.5",
        system_prompt="You are a helpful assistant.",
        max_output_tokens=8192,
        tools=[],
    )


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestSessionCreation:
    """Contract: create_session() returns EphemeralSession with correct metadata."""

    @pytest.mark.stubbed
    async def test_returns_ephemeral_session_handle(self, factory, basic_config):
        """Contract: Returns EphemeralSession, not a raw SDK session."""
        session = await factory.create_session(basic_config)
        assert isinstance(session, EphemeralSession), (
            "Contract violation: create_session() MUST return EphemeralSession, "
            f"got {type(session).__name__}"
        )

    @pytest.mark.stubbed
    async def test_session_id_is_unique_per_creation(self, factory, basic_config):
        """Contract: Each session gets a unique ID."""
        session1 = await factory.create_session(basic_config)
        session2 = await factory.create_session(basic_config)
        assert session1.id != session2.id, (
            "Contract violation: Each session MUST have a unique ID."
        )

    @pytest.mark.stubbed
    async def test_session_model_id_matches_config(self, factory, basic_config):
        """Contract: EphemeralSession.model_id matches SessionConfig.model_id."""
        session = await factory.create_session(basic_config)
        assert session.model_id == basic_config.model_id

    @pytest.mark.stubbed
    async def test_session_has_creation_timestamp(self, factory, basic_config):
        """Contract: EphemeralSession.created_at_ns is set (for timeout tracking)."""
        session = await factory.create_session(basic_config)
        assert session.created_at_ns > 0, (
            "Contract violation: created_at_ns MUST be set for timeout tracking."
        )

    @pytest.mark.stubbed
    async def test_active_count_increments_on_create(self, factory, basic_config):
        assert factory.active_session_count() == 0
        await factory.create_session(basic_config)
        assert factory.active_session_count() == 1


class TestPreToolUseDenyHook:
    """
    CRITICAL CONTRACT: preToolUse deny hook MUST be installed on every session.

    This is the mechanism that enforces Amplifier's tool sovereignty.
    If this hook is not installed, the SDK will execute tools autonomously.
    """

    @pytest.mark.stubbed
    async def test_deny_hook_is_installed_on_sdk_session(
        self, factory, basic_config, mock_sdk_client
    ):
        """
        Contract: preToolUse deny hook MUST be installed before session is returned.

        Verifies that the SDK client was called with a session config that
        includes a preToolUse hook.
        """
        await factory.create_session(basic_config)

        # Verify SDK was called
        assert mock_sdk_client.create_session.called, (
            "SDK create_session must be called"
        )

        # Verify the config passed to SDK included a hook
        sdk_call_args = mock_sdk_client.create_session.call_args
        sdk_config = sdk_call_args[0][0] if sdk_call_args[0] else sdk_call_args[1].get("config")

        # The hook must be present — exact attribute name may vary by SDK version
        has_hook = (
            hasattr(sdk_config, "hooks")
            or hasattr(sdk_config, "preToolUse")
            or hasattr(sdk_config, "pre_tool_use")
        )
        assert has_hook, (
            "CRITICAL CONTRACT VIOLATION: SDK session config MUST include "
            "preToolUse deny hook. Without this hook, the SDK will execute "
            "tools autonomously, violating Amplifier sovereignty.\n"
            f"SDK config received: {sdk_config!r}"
        )

    @pytest.mark.stubbed
    async def test_every_session_gets_deny_hook(
        self, factory, basic_config, mock_sdk_client
    ):
        """Contract: EVERY session creation installs the hook, not just the first."""
        for _ in range(3):
            await factory.create_session(basic_config)

        # Each SDK call must have had the hook
        assert mock_sdk_client.create_session.call_count == 3


class TestSessionDestruction:
    """Contract: destroy_session() releases SDK resources and never raises."""

    @pytest.mark.stubbed
    async def test_active_count_decrements_on_destroy(self, factory, basic_config):
        session = await factory.create_session(basic_config)
        assert factory.active_session_count() == 1
        await factory.destroy_session(session)
        assert factory.active_session_count() == 0

    @pytest.mark.stubbed
    async def test_sdk_destroy_is_called(
        self, factory, basic_config, mock_sdk_client
    ):
        """Contract: SDK session.destroy() is called on destruction."""
        session = await factory.create_session(basic_config)
        sdk_session = mock_sdk_client.create_session.return_value
        await factory.destroy_session(session)
        sdk_session.destroy.assert_called_once()

    @pytest.mark.stubbed
    async def test_destroy_is_idempotent(self, factory, basic_config):
        """Contract: destroy_session() is safe to call twice."""
        session = await factory.create_session(basic_config)
        await factory.destroy_session(session)
        await factory.destroy_session(session)  # Must not raise

    @pytest.mark.stubbed
    async def test_destroy_never_raises_on_sdk_error(
        self, factory, basic_config, mock_sdk_client
    ):
        """Contract: destroy_session() MUST NOT raise even if SDK destroy fails."""
        mock_sdk_client.create_session.return_value.destroy = AsyncMock(
            side_effect=RuntimeError("SDK destroy failed")
        )
        session = await factory.create_session(basic_config)
        await factory.destroy_session(session)  # Must NOT raise RuntimeError


class TestContextManager:
    """Contract: factory.session() context manager auto-destroys on exit."""

    @pytest.mark.stubbed
    async def test_session_is_active_inside_context(self, factory, basic_config):
        async with factory.session(basic_config) as session:
            assert isinstance(session, EphemeralSession)
            assert factory.active_session_count() == 1

    @pytest.mark.stubbed
    async def test_session_is_destroyed_on_normal_exit(self, factory, basic_config):
        async with factory.session(basic_config) as session:
            pass  # Normal exit
        assert factory.active_session_count() == 0

    @pytest.mark.stubbed
    async def test_session_is_destroyed_on_exception(self, factory, basic_config):
        """Contract: Session is destroyed even when an exception occurs inside."""
        with pytest.raises(ValueError):
            async with factory.session(basic_config):
                raise ValueError("something went wrong")

        assert factory.active_session_count() == 0, (
            "Contract violation: Session MUST be destroyed even on exception. "
            "Leaking sessions causes resource exhaustion."
        )


class TestErrorHandling:
    """Contract: SDK errors are wrapped via translate_sdk_error()."""

    @pytest.mark.stubbed
    async def test_sdk_session_error_raises_copilot_session_error(
        self, factory, basic_config, mock_sdk_client
    ):
        """Contract: SDK session creation failure → CopilotSessionError."""
        mock_sdk_client.create_session.side_effect = RuntimeError(
            "session creation failed"
        )
        with pytest.raises(CopilotProviderError):  # CopilotSessionError is a subclass
            await factory.create_session(basic_config)

    @pytest.mark.stubbed
    async def test_sdk_auth_error_raises_copilot_auth_error(
        self, factory, basic_config, mock_sdk_client
    ):
        """Contract: SDK 401 error → CopilotAuthError (not retryable)."""
        mock_sdk_client.create_session.side_effect = RuntimeError(
            "HTTP 401 unauthorized"
        )
        with pytest.raises(CopilotAuthError) as exc_info:
            await factory.create_session(basic_config)
        assert exc_info.value.retryable is False
```

---

### 3.5 Success Criteria

- [ ] All unit tests pass
- [ ] `preToolUse deny hook` test passes (critical — this is the sovereignty invariant)
- [ ] Context manager test: session destroyed even when exception occurs
- [ ] `destroy_session()` never raises for any input (SDK errors silently swallowed)
- [ ] `active_session_count()` returns 0 after every `destroy_session()` call
- [ ] Module is ≤300 lines
- [ ] Only SDK imports are inside `_to_sdk_config()` and the hook installation (isolated)
- [ ] `pyright --strict` reports zero errors
- [ ] Zero SDK types appear in any method signature (all `Any` or domain types)

---

## Appendix A: Dependency Graph

```
                    ┌──────────────────────────────────┐
                    │         _types.py                │
                    │  (shared domain types, no SDK)   │
                    └────────────┬─────────────────────┘
                                 │ imported by
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
   ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐
   │errors/           │  │converters/     │  │client/               │
   │  exceptions.py  │  │  tool_parsing  │  │  session_factory.py  │
   │                 │  │  .py           │  │                      │
   │ (stdlib only)   │  │ (stdlib +      │  │ (stdlib + _types +   │
   └─────────────────┘  │  _types only)  │  │  errors/exceptions)  │
                        └────────────────┘  └──────────────────────┘
```

**Rule**: Arrows only point DOWN (toward leaves). No circular imports.

---

## Appendix B: File Structure Reference

```
provider_github_copilot/
├── _types.py                    ← Section 0: Shared domain types
├── errors/
│   ├── __init__.py              ← Re-exports __all__ from exceptions.py
│   └── exceptions.py            ← MODULE 1: Error hierarchy + translate_sdk_error()
├── converters/
│   ├── __init__.py
│   └── tool_parsing.py          ← MODULE 2: parse_tool_calls() + ToolCallAccumulator
└── client/
    ├── __init__.py
    └── session_factory.py       ← MODULE 3: SessionFactory + EphemeralSession + deny hook

tests/
├── unit/
│   ├── test_error_translation.py    ← Module 1 tests
│   ├── test_tool_parsing.py         ← Module 2 tests
│   └── test_session_factory.py      ← Module 3 tests
└── property/
    └── test_tool_parsing_properties.py  ← Module 2 property tests
```

---

## Appendix C: Implementation Checklist for modular-builder

Before marking any module as "done", verify:

**For all modules**:
- [ ] All listed `__all__` symbols are implemented
- [ ] All function signatures match specifications exactly (names, types, defaults)
- [ ] All docstrings include Contract section
- [ ] `from __future__ import annotations` at top of every file
- [ ] `pyright --strict` passes
- [ ] All unit tests in this spec pass
- [ ] Module line count is within target range

**Module 1 specific**:
- [ ] `translate_sdk_error()` handles every row in the classification table
- [ ] SDK import failure is graceful (module works without SDK installed)
- [ ] `_RETRY_AFTER_PATTERN` regex matches the specified pattern

**Module 2 specific**:
- [ ] `parse_tool_calls()` is the filter-only implementation (trivial by design)
- [ ] `ToolCallAccumulator.on_complete()` returns `ToolCallBlock(arguments={})` for malformed JSON
- [ ] Property tests pass with Hypothesis

**Module 3 specific**:
- [ ] preToolUse deny hook is installed in `_to_sdk_config()` or equivalent
- [ ] Context manager `__aexit__` destroys session even when `exc_type is not None`
- [ ] `destroy_session()` swallows all SDK exceptions (never re-raises)
- [ ] SDK session objects are stored in internal dict, never returned

---

*This document is the "constitution" for implementing these three modules. Any ambiguity should be resolved in favor of the more conservative interpretation (simpler, less SDK coupling, more graceful degradation). If an implementation decision requires choosing between two approaches not covered here, the deciding question is: "Does the SDK need to know about this?" If yes, it belongs in the adapter layer. If no, keep it in domain code.*
