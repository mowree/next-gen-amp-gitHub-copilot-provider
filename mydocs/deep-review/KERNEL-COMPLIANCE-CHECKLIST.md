# Kernel Compliance Checklist — All 43 Phase 9 Features

**Authority:** AMPLIFIER-DIRECTIVE-2026-03-15.md
**Date:** 2026-03-15
**Purpose:** Pre-implementation kernel compliance verification for each feature

---

## Kernel Type Reference (Authoritative)

### `amplifier_core.llm_errors` (Error Taxonomy)
```
LLMError (base), RateLimitError, AuthenticationError, ContextLengthError,
ContentFilterError, InvalidRequestError, ProviderUnavailableError,
LLMTimeoutError, NotFoundError, StreamError, AbortError,
InvalidToolCallError, ConfigurationError, AccessDeniedError (→AuthenticationError),
NetworkError (→ProviderUnavailableError), QuotaExceededError (→RateLimitError)
```

### `amplifier_core.models` (Data Models)
```
ProviderInfo, ModelInfo, ConfigField, ModuleInfo, SessionStatus,
HookResult, ToolResult
```

### `amplifier_core.message_models` (Request/Response Envelope)
```
ChatRequest, ChatResponse, Message, ToolCall, Usage, ToolSpec,
TextBlock, ThinkingBlock, RedactedThinkingBlock, ToolCallBlock,
ToolResultBlock, ImageBlock, ReasoningBlock, ContentBlockUnion, Degradation
```

### `amplifier_core.events` (Event Constants)
```
PROVIDER_REQUEST, PROVIDER_RESPONSE, PROVIDER_ERROR, PROVIDER_RETRY,
PROVIDER_THROTTLE, TOOL_PRE, TOOL_POST, TOOL_ERROR,
SESSION_START, SESSION_END, CONTENT_BLOCK_START, CONTENT_BLOCK_DELTA,
CONTENT_BLOCK_END, USER_NOTIFICATION, ... (see events.py for full list)
```

### `amplifier_core.interfaces` (Protocols)
```
Provider, Tool, HookHandler, Orchestrator, ContextManager,
ApprovalRequest, ApprovalResponse, ApprovalProvider
```

---

## Global Anti-Patterns (Apply to ALL Features)

- [ ] ❌ `LLMProviderError` — **DOES NOT EXIST**. Use `ProviderUnavailableError`.
- [ ] ❌ `SessionCreateError` / `SessionDestroyError` — **NOT kernel types**. Use `ProviderUnavailableError`.
- [ ] ❌ Custom exception classes — **FORBIDDEN**. Use only `amplifier_core.llm_errors`.
- [ ] ❌ Custom event type enums beyond `DomainEventType` — Use kernel event constants.
- [ ] ❌ Local dataclass replacements for kernel Pydantic models — Use `amplifier_core.*` directly.
- [ ] ❌ `from amplifier_core.types import ...` — **Module does not exist**. Use `.models`, `.message_models`, `.interfaces`.

---

## Phase 1: Zero-Risk Cleanups + Sovereignty

---

### F-049: Fix Architecture Test Paths

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes (use kernel errors only)
- [ ] No custom event types (use kernel events only)
- [ ] Test path assertions use `Path("amplifier_module_provider_github_copilot")` (no `src/` prefix)
- [ ] Contract markdown files reference `amplifier_module_provider_github_copilot/` (no `src/` prefix)
- [ ] `src/` directory deleted (contains only orphan `__pycache__/`)

**Correct Import Statements:**
```python
# No kernel imports needed — this is a path fix only
from pathlib import Path
```

**Anti-patterns to Avoid:**
- [ ] Don't use `Path("src/amplifier_module_provider_github_copilot")`
- [ ] Don't use `modules/provider-core/` in contract references

---

### F-050: Mandatory Deny Hook Installation

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError` (for SDK unavailable)
- [ ] Import from `amplifier_core.models`: `HookResult` (if integrating with kernel hooks)
- [ ] Import from `amplifier_core.interfaces`: None directly (deny hook is SDK-level, not kernel hook)

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Deny hook failure raises `ProviderUnavailableError`, not a custom exception
- [ ] Deny hook uses existing `create_deny_hook()` and `deny_permission_request()` patterns
- [ ] Enforcement is at session creation time, not deferred

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import ProviderUnavailableError
```

**Anti-patterns to Avoid:**
- [ ] Don't create `DenyHookError` or `SovereigntyViolationError` custom exceptions
- [ ] Don't skip deny hook registration in any code path
- [ ] Don't use `assert` for enforcement (stripped by `-O`)

---

### F-077: Delete Tombstone Test Files

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] No custom event types
- [ ] Deletion only — no new code introduced
- [ ] Remaining tests still pass after deletion

**Correct Import Statements:**
```python
# No kernel imports needed — file deletion only
```

**Anti-patterns to Avoid:**
- [ ] Don't delete active test files (only tombstones with no test functions)
- [ ] Don't introduce replacement test files in this feature

---

### F-079: Add py.typed Marker

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] `py.typed` marker file is empty (PEP 561)
- [ ] Placed at `amplifier_module_provider_github_copilot/py.typed`
- [ ] `pyproject.toml` includes `py.typed` in package data

**Correct Import Statements:**
```python
# No kernel imports needed — marker file only
```

**Anti-patterns to Avoid:**
- [ ] Don't put content in the `py.typed` file
- [ ] Don't forget to include in wheel packaging

---

### F-084: Remove Redundant Path Import

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] `from pathlib import Path` removed from `provider.py` top-level (already imported via deferred path)
- [ ] No functional change — Path still available where needed via local imports
- [ ] All existing Path usages still work

**Correct Import Statements:**
```python
# Remove redundant top-level Path import from provider.py
# Keep local `from pathlib import Path` inside functions that need it
```

**Anti-patterns to Avoid:**
- [ ] Don't remove Path imports that are actually used
- [ ] Don't break deferred import patterns

---

## Phase 2: Config Foundation

---

### F-074: Config Not in Wheel

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ConfigurationError` (for config load failures)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes for config failures
- [ ] Config files (`errors.yaml`, `events.yaml`, `models.yaml`) included inside `amplifier_module_provider_github_copilot/` package
- [ ] `importlib.resources` used for config access (not relative `Path(__file__).parent.parent`)
- [ ] Config load failures raise `ConfigurationError` or degrade gracefully

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import ConfigurationError
from importlib import resources
```

**Anti-patterns to Avoid:**
- [ ] Don't hardcode file paths relative to project root
- [ ] Don't leave config outside the wheel package
- [ ] Don't create custom `ConfigLoadError` exception

---

### F-081: Fix Context Extraction in Client Error Loading

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None (uses existing error_translation module)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `_load_error_config_once()` in `client.py` loads `context_extraction` field from YAML
- [ ] `ErrorMapping` dataclass already has `context_extraction` field — just needs parsing
- [ ] Kernel error types enriched with extracted context (via `_format_context_suffix`)

**Correct Import Statements:**
```python
from ..error_translation import ContextExtraction, ErrorConfig, ErrorMapping
```

**Anti-patterns to Avoid:**
- [ ] Don't create new error types for context extraction failures
- [ ] Don't silently drop `context_extraction` from YAML (the current bug)

---

### F-078: Add context_window to Fallback Config

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: `ProviderInfo` (verify `defaults` dict shape)
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `ProviderInfo.defaults` must include `context_window` key
- [ ] Fallback `_default_provider_config()` includes `context_window` in defaults
- [ ] Value matches kernel `ModelInfo.context_window` type (int)

**Correct Import Statements:**
```python
from amplifier_core.models import ProviderInfo  # already imported in provider.py
```

**Anti-patterns to Avoid:**
- [ ] Don't add `context_window` as a top-level field on a custom type
- [ ] Don't use string value for `context_window` (must be int)

---

## Phase 3: P0 Critical Path

---

### F-072: Real SDK Path Error Translation

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMError`, `ProviderUnavailableError` (fallback type)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `provider.py` real SDK path (lines 477-495) wrapped in `try/except`
- [ ] Caught exceptions translated via `translate_sdk_error()`
- [ ] Already-translated `LLMError` re-raised without double-wrapping
- [ ] Default fallback is `ProviderUnavailableError` (**NOT** `LLMProviderError`)

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError
from .error_translation import translate_sdk_error, load_error_config
```

**Anti-patterns to Avoid:**
- [ ] ❌ Don't use `LLMProviderError` (DOES NOT EXIST)
- [ ] Don't define custom exceptions
- [ ] Don't let raw SDK exceptions escape provider boundary
- [ ] Don't double-wrap already-translated `LLMError` instances

---

### F-073: Real SDK Path Error Test

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError`, `RateLimitError`, `AuthenticationError`, `LLMError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] Tests assert kernel error types, not custom types
- [ ] `RuntimeError` → `ProviderUnavailableError` (fallback) — **NOT** `LLMProviderError`
- [ ] Test verifies `provider` attribute is set to `"github-copilot"`
- [ ] Test verifies exception chaining (`__cause__` preserves original)

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import (
    AuthenticationError,
    LLMError,
    ProviderUnavailableError,
    RateLimitError,
)
```

**Anti-patterns to Avoid:**
- [ ] ❌ Don't assert `LLMProviderError` (DOES NOT EXIST)
- [ ] Don't create test-only exception classes
- [ ] Don't test against `Exception` base class — test specific kernel types

---

### F-052: Real SDK Streaming Pipeline

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError`, `StreamError`, `LLMError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: `ChatResponse`

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] SDK `SESSION_ERROR` events raise `ProviderUnavailableError`
- [ ] Stream interruptions raise `StreamError` (mid-stream failures)
- [ ] Returns `ChatResponse` via `StreamingAccumulator.to_chat_response()`
- [ ] Uses SDK `on()` + queue pattern (verified), not `AsyncIterator`
- [ ] Already-translated `LLMError` not double-wrapped

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError, StreamError
from amplifier_core import ChatResponse
```

**Anti-patterns to Avoid:**
- [ ] Don't use `send_message()` AsyncIterator (doesn't exist in SDK)
- [ ] Don't create `StreamingError` custom exception
- [ ] Don't bypass `translate_sdk_error()` for SDK errors

---

### F-051: Defensive Event Config Loading

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None (graceful degradation, no errors raised)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `load_event_config()` handles malformed YAML gracefully (returns default `EventConfig`)
- [ ] No crash on missing keys, bad types, or corrupt YAML
- [ ] Existing `DomainEventType` enum used (not new event types)

**Correct Import Statements:**
```python
# No new kernel imports needed — uses existing streaming.py types
import yaml
from pathlib import Path
```

**Anti-patterns to Avoid:**
- [ ] Don't raise `ConfigurationError` for event config (graceful degradation pattern)
- [ ] Don't create custom `EventConfigError`
- [ ] Don't change `DomainEventType` enum values

---

## Phase 4: Robustness Hardening

---

### F-085: Add Timeout Enforcement Real SDK Path

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMTimeoutError`, `LLMError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes — `asyncio.TimeoutError` translated to `LLMTimeoutError`
- [ ] `LLMTimeoutError` created with `provider="github-copilot"`, `retryable=True`
- [ ] Timeout wraps `sdk_session.send_and_wait()` via `asyncio.wait_for()`
- [ ] Absorbs F-058 scope — single implementation point

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import LLMTimeoutError, LLMError
import asyncio
```

**Anti-patterns to Avoid:**
- [ ] Don't create `SDKTimeoutError` custom exception
- [ ] Don't use bare `TimeoutError` — translate to `LLMTimeoutError`
- [ ] Don't implement F-058 separately (absorbed into this feature)

---

### F-082: Wire Provider close() to Client close()

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `provider.close()` delegates to `self._client.close()`
- [ ] Errors during close are logged, not raised (existing pattern in `client.close()`)
- [ ] Provider protocol `close()` signature preserved (no return value change)

**Correct Import Statements:**
```python
# No new kernel imports needed — wiring only
```

**Anti-patterns to Avoid:**
- [ ] Don't raise exceptions from `close()` — log and swallow
- [ ] Don't create a `CloseError` custom type
- [ ] Don't change the `async def close(self) -> None` signature

---

### F-053: Unify Error Config Loading

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ConfigurationError` (optional, for load failures)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Single config loading path (eliminate duplication between `error_translation.py` and `client.py`)
- [ ] `ErrorConfig`, `ErrorMapping`, `ContextExtraction` dataclasses preserved
- [ ] `KERNEL_ERROR_MAP` dict unchanged (maps string names → kernel error classes)

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import ConfigurationError  # optional
from .error_translation import ErrorConfig, load_error_config
```

**Anti-patterns to Avoid:**
- [ ] Don't create a second `KERNEL_ERROR_MAP`
- [ ] Don't change the `translate_sdk_error()` signature
- [ ] Don't hardcode error mappings (must remain config-driven)

---

### F-054: Response Extraction Recursion Guard

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `extract_response_content()` has max recursion depth (prevent infinite `.data` chains)
- [ ] Returns empty string on max depth (graceful degradation)
- [ ] No change to return type (still `str`)

**Correct Import Statements:**
```python
# No new kernel imports needed — internal safety guard only
```

**Anti-patterns to Avoid:**
- [ ] Don't raise `RecursionError` — return `""` on max depth
- [ ] Don't create `ExtractionError` custom exception
- [ ] Don't change the function signature of `extract_response_content()`

---

### F-055: Streaming Accumulator Completion Guard

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: `ChatResponse` (via `to_chat_response()`)

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `StreamingAccumulator.to_chat_response()` produces valid `ChatResponse` even if `is_complete=False`
- [ ] Guard ensures `TURN_COMPLETE` event is synthesized if missing
- [ ] `ChatResponse` content blocks use kernel `TextBlock`/`ThinkingBlock`

**Correct Import Statements:**
```python
from amplifier_core import ChatResponse, TextBlock, ThinkingBlock, ToolCall, Usage
```

**Anti-patterns to Avoid:**
- [ ] Don't create `IncompleteStreamError` custom exception
- [ ] Don't return `None` from `to_chat_response()` — always return valid `ChatResponse`

---

### F-056: SDK Client Failed Start Cleanup

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] If `CopilotClient.start()` fails, `self._owned_client` is reset to `None`
- [ ] Failed start raises `ProviderUnavailableError` (via `translate_sdk_error`)
- [ ] No resource leaks on partial initialization

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import ProviderUnavailableError
```

**Anti-patterns to Avoid:**
- [ ] Don't create `ClientStartError` custom exception
- [ ] Don't leave `self._owned_client` pointing to failed client
- [ ] Don't swallow the start error silently

---

## Phase 5: Error & Integration

---

### F-066: Error Translation Safety

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMError`, `ProviderUnavailableError` (all kernel error types via `KERNEL_ERROR_MAP`)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `_matches_mapping()` handles regex errors gracefully (no crash on bad patterns)
- [ ] `translate_sdk_error()` never raises — always returns an `LLMError`
- [ ] `KERNEL_ERROR_MAP` lookup uses `.get()` with `ProviderUnavailableError` fallback

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError
# All 16 kernel error types already imported in error_translation.py
```

**Anti-patterns to Avoid:**
- [ ] Don't add custom error types to `KERNEL_ERROR_MAP`
- [ ] Don't let `translate_sdk_error()` raise on internal errors
- [ ] Don't use `re.compile()` without error handling

---

### F-061: Error Config Missing Mappings

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `AbortError`, `ContextLengthError` (missing from current config)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `config/errors.yaml` updated with mappings for all 16 kernel error types
- [ ] Added: `AbortError`, `ContextLengthError` mappings (identified as missing)
- [ ] Each mapping's `kernel_error` field matches a key in `KERNEL_ERROR_MAP`

**Correct Import Statements:**
```python
# No code imports needed — YAML config changes only
# KERNEL_ERROR_MAP already includes all 16 types
```

**Anti-patterns to Avoid:**
- [ ] Don't add non-kernel error type names to `kernel_error` field in YAML
- [ ] Don't remove existing working mappings
- [ ] Don't hardcode mappings in Python (keep config-driven)

---

### F-068: Event Classification Validation

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] No custom event types — validates against existing `DomainEventType` enum
- [ ] `config/events.yaml` bridge mappings reference valid `DomainEventType` values
- [ ] Validation at config load time, not at event translation time

**Correct Import Statements:**
```python
from .streaming import DomainEventType, EventConfig
```

**Anti-patterns to Avoid:**
- [ ] Don't add new `DomainEventType` values without contract review
- [ ] Don't create `EventValidationError` custom exception
- [ ] Don't change `EventClassification` enum

---

### F-059: ChatRequest Multi-Turn Context

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: `ChatRequest`, `Message`

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `complete()` extracts ALL messages from `ChatRequest.messages` (not just last)
- [ ] Message roles preserved (`system`, `user`, `assistant`, `tool`)
- [ ] Kernel `Message` type used for message extraction (not raw dicts)

**Correct Import Statements:**
```python
from amplifier_core.message_models import ChatRequest, Message
```

**Anti-patterns to Avoid:**
- [ ] Don't flatten multi-turn to single prompt (loses context)
- [ ] Don't create custom `ConversationContext` type
- [ ] Don't ignore message roles during extraction

---

### F-086: Handle Session Disconnect Failures

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None (disconnect errors are logged, not raised)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Disconnect failures logged at WARNING level (existing pattern)
- [ ] Disconnect errors never mask the original error
- [ ] Track disconnect success/failure for observability

**Correct Import Statements:**
```python
import logging
# No new kernel imports needed
```

**Anti-patterns to Avoid:**
- [ ] Don't raise on disconnect failure (masks original error)
- [ ] Don't create `DisconnectError` custom exception
- [ ] Don't silently swallow disconnect errors (must log)

---

## Phase 6: Retry System

---

### F-075: Retry YAML Dead Config

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `config/retry.yaml` deleted (dead config not consumed by any code)
- [ ] No references to `retry.yaml` remain in codebase
- [ ] No functional change

**Correct Import Statements:**
```python
# No kernel imports needed — file deletion only
```

**Anti-patterns to Avoid:**
- [ ] Don't create a replacement retry config (F-060 will handle retry properly)
- [ ] Don't remove `config/errors.yaml` or `config/events.yaml` (those are active)

---

### F-060: Config-Driven Retry

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMError`, `RateLimitError`, `LLMTimeoutError`, `ProviderUnavailableError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Retry decisions based on `LLMError.retryable` attribute
- [ ] `RateLimitError.retry_after` respected when available
- [ ] Retry config loaded from YAML (not hardcoded)
- [ ] Uses kernel error `delay_multiplier` attribute for backoff

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import (
    LLMError,
    LLMTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
```

**Anti-patterns to Avoid:**
- [ ] Don't create `RetryableError` custom exception
- [ ] Don't ignore `LLMError.retryable` flag
- [ ] Don't hardcode retry delays (use config + `retry_after` + `delay_multiplier`)

---

### F-090: Behavioral Tests for Behaviors Contract

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMError`, `ProviderUnavailableError`, `RateLimitError`, `AuthenticationError`
- [ ] Import from `amplifier_core.models`: `ProviderInfo`, `ModelInfo`
- [ ] Import from `amplifier_core.message_models`: `ChatRequest`, `ChatResponse`, `Message`, `ToolCall`

**Kernel Compliance Checks:**
- [ ] Tests verify kernel type compliance (not internal types)
- [ ] `complete()` returns `ChatResponse` (kernel type)
- [ ] `get_info()` returns `ProviderInfo` (kernel type)
- [ ] `list_models()` returns `list[ModelInfo]` (kernel type)
- [ ] `parse_tool_calls()` returns `list[ToolCall]` (kernel type)
- [ ] Error translation produces kernel `LLMError` subtypes

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import (
    AuthenticationError,
    LLMError,
    ProviderUnavailableError,
    RateLimitError,
)
from amplifier_core.models import ModelInfo, ProviderInfo
from amplifier_core.message_models import ChatRequest, ChatResponse, Message, ToolCall
```

**Anti-patterns to Avoid:**
- [ ] Don't test internal types (`CompletionRequest`, `DomainEvent`) in behavioral tests
- [ ] Don't assert custom exception types
- [ ] Don't use `isinstance(response, dict)` — assert `ChatResponse`

---

## Phase 7: Structural Refactoring

---

### F-067: Test Quality Improvements

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: All error types used in tests
- [ ] Import from `amplifier_core.models`: `ProviderInfo`, `ModelInfo`
- [ ] Import from `amplifier_core.message_models`: `ChatResponse`, `ToolCall`

**Kernel Compliance Checks:**
- [ ] No custom error classes in tests
- [ ] Test assertions use kernel types (not local/mock types)
- [ ] Mock returns match kernel type signatures
- [ ] `MagicMock` coordinators replaced with or validated against real protocols where feasible

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError
from amplifier_core.models import ModelInfo, ProviderInfo
from amplifier_core.message_models import ChatResponse, ToolCall
```

**Anti-patterns to Avoid:**
- [ ] Don't create mock-only exception types
- [ ] Don't assert against `dict` when kernel provides typed models
- [ ] Don't leave tests using obsolete type assertions

---

### F-088: Create _imports.py SDK Quarantine

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError` (for import failures)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] All `copilot.*` SDK imports consolidated into `sdk_adapter/_imports.py`
- [ ] SDK import failure raises `ProviderUnavailableError` (not `ImportError`)
- [ ] No SDK types leak beyond `sdk_adapter/` boundary

**Correct Import Statements:**
```python
# In _imports.py:
from amplifier_core.llm_errors import ProviderUnavailableError

try:
    from copilot import CopilotClient
    from copilot.types import PermissionRequestResult
    # ... other SDK imports
except ImportError as e:
    raise ProviderUnavailableError(f"Copilot SDK not installed: {e}") from e
```

**Anti-patterns to Avoid:**
- [ ] Don't import SDK types in `provider.py` or `streaming.py`
- [ ] Don't create `SDKImportError` custom exception
- [ ] Don't use bare `ImportError` at module level (translate to kernel type)

---

### F-063: SDK Boundary Structure

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] SDK imports only via `_imports.py` (after F-088)
- [ ] `sdk_adapter/` exports only domain types, not SDK types
- [ ] `__init__.py` re-exports are minimal and SDK-free

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import ProviderUnavailableError
from .sdk_adapter.client import CopilotClientWrapper, create_deny_hook
from .sdk_adapter.types import SessionConfig, SDKSession
```

**Anti-patterns to Avoid:**
- [ ] Don't expose `copilot.*` types outside `sdk_adapter/`
- [ ] Don't create new SDK wrapper types that duplicate kernel types

---

### F-069: Remove complete_fn Dead Code

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Removed: `self._complete_fn` from `__init__`
- [ ] Removed: `SDKCreateFn` type alias (if unused after removal)
- [ ] Removed: module-level `complete()` and `complete_and_collect()` functions (if dead)
- [ ] All remaining code uses kernel types correctly

**Correct Import Statements:**
```python
# Removal — verify no new imports needed
```

**Anti-patterns to Avoid:**
- [ ] Don't remove code that tests still depend on (verify first)
- [ ] Don't remove `_complete_internal()` if still used by test injection path

---

### F-070: Cleanup Deferred Imports

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMError`, `ProviderUnavailableError` (move to top-level)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Deferred `from .error_translation import ...` inside functions moved to top-level
- [ ] Top-level imports use kernel types directly
- [ ] No circular import issues after consolidation

**Correct Import Statements:**
```python
# Move from inside functions to top-level:
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError
from .error_translation import translate_sdk_error, load_error_config, ErrorConfig
```

**Anti-patterns to Avoid:**
- [ ] Don't introduce circular imports
- [ ] Don't defer kernel imports (they're always available)

---

### F-089: Align SessionConfig Shape with Contract

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `SessionConfig` dataclass in `sdk_adapter/types.py` aligned with SDK contract
- [ ] Unused fields removed (absorbs F-071 scope)
- [ ] Fields match what `client.py` actually passes to SDK `create_session()`

**Correct Import Statements:**
```python
from dataclasses import dataclass
# SessionConfig is a local domain type, not a kernel type
```

**Anti-patterns to Avoid:**
- [ ] Don't make `SessionConfig` a kernel type (it's SDK-specific)
- [ ] Don't implement F-071 separately (absorbed here)
- [ ] Don't add fields that the SDK doesn't consume

---

### F-087: Strengthen complete Parameter Type

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: `ChatRequest`

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `complete()` parameter type narrowed from `Any` to `ChatRequest`
- [ ] Internal `CompletionRequest` conversion preserved for backward compatibility
- [ ] Type annotation matches Provider protocol: `async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse`

**Correct Import Statements:**
```python
from amplifier_core.message_models import ChatRequest
from amplifier_core import ChatResponse
```

**Anti-patterns to Avoid:**
- [ ] Don't break existing callers that pass `CompletionRequest`
- [ ] Don't change the return type (must remain `ChatResponse`)
- [ ] Don't make `ChatRequest` the only accepted type without migration path

---

## Phase 8: Provider Decomposition

---

### F-065: Provider Decomposition

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `LLMError`, `ProviderUnavailableError` (in completion.py)
- [ ] Import from `amplifier_core.models`: `ProviderInfo`, `ModelInfo` (in provider.py)
- [ ] Import from `amplifier_core.message_models`: `ChatRequest`, `ChatResponse`, `ToolCall` (in response.py)

**Kernel Compliance Checks:**
- [ ] No custom error classes in any extracted module
- [ ] Extracted `completion.py` imports kernel error types
- [ ] Extracted `response.py` uses kernel `ChatResponse`, `TextBlock`, `ThinkingBlock`
- [ ] `provider.py` still implements `Provider` protocol (4 methods + 1 property)
- [ ] All public methods return kernel types

**Correct Import Statements:**
```python
# provider.py (after decomposition):
from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
from amplifier_core.llm_errors import LLMError

# completion.py (new extracted module):
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError
from amplifier_core import ChatResponse

# response.py (new extracted module):
from amplifier_core import ChatResponse, TextBlock, ThinkingBlock, ToolCall, Usage
```

**Anti-patterns to Avoid:**
- [ ] Don't implement before ALL other provider.py features land
- [ ] Don't change public API surface during decomposition
- [ ] Don't introduce new types — only reorganize existing kernel types

---

## Phase 9: Test & Packaging Polish

---

### F-062: Architecture Test Hardening

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None (test infrastructure)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] Architecture tests verify kernel type usage (not internal types)
- [ ] Tests assert no custom exception classes in production code
- [ ] Tests verify `amplifier_core.llm_errors` imports present
- [ ] Path assertions use correct package path (F-049 prerequisite)

**Correct Import Statements:**
```python
# Architecture test imports:
import ast
from pathlib import Path
# No kernel type imports needed in arch tests themselves
```

**Anti-patterns to Avoid:**
- [ ] Don't test against `src/` paths (use `amplifier_module_provider_github_copilot/`)
- [ ] Don't whitelist custom exception classes
- [ ] Don't make tests that pass vacuously on empty directories

---

### F-076: Fix Async Mock Warning

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] `asyncio.iscoroutinefunction()` deprecation warnings resolved
- [ ] Mock async functions use `AsyncMock` instead of `MagicMock` where appropriate
- [ ] No functional change to test behavior

**Correct Import Statements:**
```python
from unittest.mock import AsyncMock, MagicMock, patch
```

**Anti-patterns to Avoid:**
- [ ] Don't suppress the warning — fix the root cause
- [ ] Don't change mock return values while fixing async issues

---

### F-083: Fix Test Contract Events Enum Type

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] No custom error classes
- [ ] Test uses `DomainEventType.CONTENT_DELTA.value` (string) not `DomainEventType.CONTENT_DELTA` (enum member) for string comparisons
- [ ] Enum member vs string value usage is consistent across all tests

**Correct Import Statements:**
```python
from amplifier_module_provider_github_copilot.streaming import DomainEventType
```

**Anti-patterns to Avoid:**
- [ ] Don't compare enum members with `==` against raw strings
- [ ] Don't create string constants duplicating enum values

---

### F-091: Ephemeral Session Invariant Tests

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: `ProviderUnavailableError`, `LLMError`
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: `ChatResponse`

**Kernel Compliance Checks:**
- [ ] Tests verify deny hook always installed (sovereignty invariant)
- [ ] Tests verify session always destroyed in `finally` block
- [ ] Tests verify errors translated to kernel `LLMError` types
- [ ] Tests verify `ChatResponse` returned (not raw SDK response)

**Correct Import Statements:**
```python
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError
from amplifier_core.message_models import ChatResponse
```

**Anti-patterns to Avoid:**
- [ ] Don't test with `MagicMock` that bypasses protocol checks
- [ ] Don't assert raw SDK types in invariant tests
- [ ] Don't test implementation details — test behavioral invariants

---

### F-064: PyPI Publishing Readiness

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None (packaging only)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] `pyproject.toml` lists `amplifier-core` as dependency
- [ ] Package version follows semantic versioning
- [ ] `py.typed` marker included (F-079 prerequisite)
- [ ] Config files included in wheel (F-074 prerequisite)
- [ ] Entry point registered correctly

**Correct Import Statements:**
```python
# No runtime kernel imports — packaging configuration only
```

**Anti-patterns to Avoid:**
- [ ] Don't pin `amplifier-core` to exact version (use compatible range)
- [ ] Don't forget to include config/ and py.typed in wheel
- [ ] Don't publish without all P0 features complete

---

### F-080: Add Missing PyPI Metadata

**Kernel Types Required:**
- [ ] Import from `amplifier_core.llm_errors`: None (metadata only)
- [ ] Import from `amplifier_core.models`: None
- [ ] Import from `amplifier_core.message_models`: None

**Kernel Compliance Checks:**
- [ ] `pyproject.toml` has complete metadata (description, author, license, classifiers)
- [ ] `bundle.md` metadata aligns with `pyproject.toml`
- [ ] No kernel types needed — metadata only

**Correct Import Statements:**
```python
# No kernel imports — pyproject.toml and bundle.md changes only
```

**Anti-patterns to Avoid:**
- [ ] Don't omit `amplifier-core` from dependencies list
- [ ] Don't use incorrect classifier for module type

---

## DROPPED / SUPERSEDED Features (No Implementation Required)

---

### F-057: Provider Close Cleanup — ❌ DROPPED

**Status:** Superseded by F-082
**Action:** None — F-082 covers the same scope

---

### F-058: SDK Request Timeout Enforcement — ❌ DROPPED

**Status:** Superseded by F-085
**Action:** None — F-085 absorbs this scope

---

### F-071: Remove Unused SessionConfig Fields — ❌ SUPERSEDED

**Status:** Superseded by F-089
**Action:** None — F-089 absorbs this scope

---

## Summary Matrix

| Feature | Phase | Kernel Errors | Kernel Models | Kernel Messages | Custom Types Allowed |
|---------|-------|---------------|---------------|-----------------|---------------------|
| F-049 | 1 | None | None | None | None |
| F-050 | 1 | ProviderUnavailableError | HookResult (optional) | None | None |
| F-077 | 1 | None | None | None | None |
| F-079 | 1 | None | None | None | None |
| F-084 | 1 | None | None | None | None |
| F-074 | 2 | ConfigurationError | None | None | None |
| F-081 | 2 | None (existing) | None | None | None |
| F-078 | 2 | None | ProviderInfo | None | None |
| F-072 | 3 | LLMError, ProviderUnavailableError | None | None | None |
| F-073 | 3 | Multiple error types | None | None | None |
| F-052 | 3 | ProviderUnavailableError, StreamError | None | ChatResponse | None |
| F-051 | 3 | None | None | None | None |
| F-085 | 4 | LLMTimeoutError | None | None | None |
| F-082 | 4 | None | None | None | None |
| F-053 | 4 | ConfigurationError (optional) | None | None | None |
| F-054 | 4 | None | None | None | None |
| F-055 | 4 | None | None | ChatResponse | None |
| F-056 | 4 | ProviderUnavailableError | None | None | None |
| F-066 | 5 | All 16 error types | None | None | None |
| F-061 | 5 | AbortError, ContextLengthError | None | None | None |
| F-068 | 5 | None | None | None | None |
| F-059 | 5 | None | None | ChatRequest, Message | None |
| F-086 | 5 | None | None | None | None |
| F-075 | 6 | None | None | None | None |
| F-060 | 6 | RateLimitError, LLMTimeoutError+ | None | None | None |
| F-090 | 6 | Multiple error types | ProviderInfo, ModelInfo | ChatRequest, ChatResponse+ | None |
| F-067 | 7 | Multiple error types | ProviderInfo, ModelInfo | ChatResponse, ToolCall | None |
| F-088 | 7 | ProviderUnavailableError | None | None | None |
| F-063 | 7 | ProviderUnavailableError | None | None | None |
| F-069 | 7 | None | None | None | None |
| F-070 | 7 | LLMError, ProviderUnavailableError | None | None | None |
| F-089 | 7 | None | None | None | None |
| F-087 | 7 | None | None | ChatRequest | None |
| F-065 | 8 | LLMError, ProviderUnavailableError | ProviderInfo, ModelInfo | ChatRequest, ChatResponse+ | None |
| F-062 | 9 | None | None | None | None |
| F-076 | 9 | None | None | None | None |
| F-083 | 9 | None | None | None | None |
| F-091 | 9 | ProviderUnavailableError, LLMError | None | ChatResponse | None |
| F-064 | 9 | None | None | None | None |
| F-080 | 9 | None | None | None | None |
| F-057 | — | ❌ DROPPED | — | — | — |
| F-058 | — | ❌ DROPPED | — | — | — |
| F-071 | — | ❌ SUPERSEDED | — | — | — |

---

**END OF CHECKLIST**

*Generated: 2026-03-15 from kernel source at reference-only/amplifier-core/python/amplifier_core/*
*Authority: AMPLIFIER-DIRECTIVE-2026-03-15.md*
