# F-018: Aggressive Simplification

## Overview

Reduce codebase from ~1,781 lines to ~360 lines (within 20% of 300-line target).
This addresses the 490% budget overrun identified in architectural review.

**Three diseases to cure:**
1. **Speculative types** — dataclasses for callers that don't exist yet
2. **Redundant layers** — session_factory.py and completion.py add indirection with no value
3. **Fallback boilerplate** — 165 lines of error classes waiting for an import

---

## Change 1: Delete loop_control.py (Save 134 lines)

### Problem

The brainstorm explicitly agreed: "SDK loop is server-side, no LoopController class needed."
The deny hook in session_factory.py already blocks all tool execution.
`LoopController` solves a hypothetical problem:
- `LoopState` tracks state nobody reads
- `LoopExitMethod` enum for values nobody switches on
- The abort callback nothing wires up

### Action

**Delete entirely**: `src/amplifier_module_provider_github_copilot/sdk_adapter/loop_control.py`

**Update** `sdk_adapter/__init__.py` — remove any loop_control imports/exports.

**Delete test file**: `tests/test_loop_control.py`

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Change 2: Simplify error_translation.py (394 → ~80 lines, Save ~314 lines)

### Problem

165 lines (lines 34-199) are 8 error class definitions that are identical LLMError subclasses.
The TODO already says "import from amplifier-core."

### Action

**Replace** the 8 error class definitions (lines 34-199) with a factory:

```python
# After imports, before translate_sdk_error

def _make_error_class(name: str, default_retryable: bool) -> type:
    """Create an LLMError subclass with fixed retryable default."""
    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        retryable: bool = default_retryable,
        retry_after: float | None = None,
    ) -> None:
        self.message = message
        self.provider = provider
        self.model = model
        self.retryable = retryable
        self.retry_after = retry_after
        super(Exception, self).__init__(message)

    return type(name, (LLMError,), {"__init__": __init__})


# Create all error types via factory (8 lines instead of 165)
AuthenticationError = _make_error_class("AuthenticationError", False)
RateLimitError = _make_error_class("RateLimitError", True)
ContentFilterError = _make_error_class("ContentFilterError", False)
ModelNotFoundError = _make_error_class("ModelNotFoundError", False)
ContextLengthError = _make_error_class("ContextLengthError", False)
ServiceUnavailableError = _make_error_class("ServiceUnavailableError", True)
ProviderUnavailableError = _make_error_class("ProviderUnavailableError", True)
UnknownProviderError = _make_error_class("UnknownProviderError", False)
```

**Keep**: `LLMError` base class, `ErrorConfig`, `load_error_config()`, `translate_sdk_error()`.

**Remove**: All individual class definitions with their verbose docstrings.

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Change 3: Delete session_factory.py (Save 157 lines)

### Problem

Redundant with `client.py`. Both create sessions with deny hooks. The split creates confusion:
- `create_ephemeral_session()` raises `ProviderUnavailableError` unless you inject `sdk_create_fn`
- `client.py` has the real `session()` context manager that actually works
- `destroy_session()` is 10 lines that just calls `session.disconnect()`
- `_create_breach_detector()` is marked `reportUnusedFunction` — dead code

### Action

**Step 3a: Move essential code to client.py**

Add to `client.py` (at top, after imports):
```python
# Deny hook constant
DENY_ALL: dict[str, str] = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty - tools executed by kernel only",
}


def create_deny_hook() -> Callable[[Any, Any], Awaitable[dict[str, str]]]:
    """Create async deny hook for SDK pre_tool_use callback."""
    async def deny(input_data: Any, invocation: Any) -> dict[str, str]:
        return DENY_ALL
    return deny
```

**Step 3b: Update completion.py**

Replace imports:
```python
# OLD
from .session_factory import create_deny_hook, destroy_session

# NEW
from .sdk_adapter.client import CopilotClientWrapper, create_deny_hook
```

Update `complete()` to use `CopilotClientWrapper.session()` context manager instead of `create_ephemeral_session()`.

**Step 3c: Delete session_factory.py**

Delete: `src/amplifier_module_provider_github_copilot/session_factory.py`

**Step 3d: Update tests**

- Delete tests that only test session_factory internals
- Update tests that import from session_factory to import from client.py

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Change 4: Simplify client.py (271 → ~80 lines, Save ~191 lines)

### Problem

Was supposed to be ~50 lines. Current bloat:
- `AuthStatus` dataclass (15 lines) — not used by any caller
- `get_auth_status()` (50 lines) — not used by any caller
- `list_models()` (20 lines) — not called by provider.py
- `CopilotSessionWrapper` — `Any` with extra steps

### Action

**Delete** from client.py:
- `AuthStatus` dataclass
- `CopilotSessionWrapper` class (use raw session, it's already opaque `Any`)
- `get_auth_status()` method
- `list_models()` method

**Keep**:
- `_resolve_token()` — essential
- `CopilotClientWrapper.__init__` + `_get_client()` — essential
- `session()` context manager — essential (but simplify to yield raw SDK session)
- `close()` — essential

**Target**: ~80 lines total

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Change 5: Merge completion.py into provider.py (Save ~189 lines)

### Problem

`completion.py` is glue between provider and client. With session_factory deleted:
- `complete()` async generator becomes 15 lines inside provider
- `complete_and_collect()` is just accumulator logic
- `CompletionRequest` and `CompletionConfig` are intermediate types adding indirection

### Action

**Step 5a: Move core logic to provider.py**

In `provider.py`, add the `complete()` async generator directly (simplified):

```python
async def complete(
    self,
    messages: Sequence[Message],
    *,
    tools: Sequence[Tool] | None = None,
    tool_choice: str | None = None,
    **kwargs: Any,
) -> AsyncIterator[ProviderEvent]:
    """Stream completion from GitHub Copilot SDK."""
    async with self._client.session(model=self._model) as session:
        # Send prompt
        prompt = self._build_prompt(messages, tools, tool_choice)
        async for event in session.send(prompt):
            yield translate_event(event)
```

**Step 5b: Delete completion.py**

Delete: `src/amplifier_module_provider_github_copilot/completion.py`

**Step 5c: Update imports**

Update `__init__.py` to not export completion module.

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Change 6: Simplify provider.py (213 → ~70 lines, Save ~143 lines)

### Problem

5 dataclasses (50 lines) not used outside this file yet:
- `ProviderDefaults`
- `ProviderInfo`
- `ModelInfo`
- `ChatRequest`
- `ChatResponse`

These are speculative protocol types.

### Action

**Delete** all dataclasses that have no callers:
- `ProviderDefaults`
- `ProviderInfo`
- `ModelInfo`
- `ChatRequest`
- `ChatResponse`

**Keep**:
- `GitHubCopilotProvider` class with `name`, `complete()`, `parse_tool_calls()`

**Target**: ~70 lines

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Change 7: Simplify streaming.py (274 → ~120 lines, Save ~154 lines)

### Problem

Verbose docstrings repeating the code (~40 lines of comments).
`StreamingAccumulator` uses Java-style `_private` + property pattern.

### Action

**Trim**:
- Remove excessive docstrings (keep one-liners)
- Simplify `StreamingAccumulator` to plain dataclass with `add()` method
- Remove property wrappers

**Keep**:
- `DomainEvent` dataclass
- `DomainEventType` enum
- `load_event_config()` — essential
- `translate_event()` — essential
- `StreamingAccumulator.add()` logic — essential

**Target**: ~120 lines

### Verification

```bash
uv run pyright src/
uv run pytest tests/ -v --tb=short
```

---

## Projected Result

| File | Before | After | Saved |
|------|--------|-------|-------|
| `__init__.py` | 12 | 12 | 0 |
| `error_translation.py` | 394 | 80 | 314 |
| `sdk_adapter/loop_control.py` | 134 | **DELETE** | 134 |
| `sdk_adapter/client.py` | 271 | 80 | 191 |
| `session_factory.py` | 157 | **DELETE** | 157 |
| `provider.py` | 213 | 70 | 143 |
| `completion.py` | 189 | **DELETE** | 189 |
| `streaming.py` | 274 | 120 | 154 |
| `tool_parsing.py` | 83 | 60 | 23 |
| `sdk_adapter/__init__.py` | 22 | 15 | 7 |
| `sdk_adapter/types.py` | 32 | 25 | 7 |
| **Total** | **1,781** | **~362** | **~1,419** |

---

## Acceptance Criteria

1. **Line count**: ~360 lines (within 20% of 300 target)
2. **pyright passes**: 0 errors
3. **All tests pass**: (updated tests)
4. **Files deleted**:
   - loop_control.py
   - session_factory.py
   - completion.py
5. **No speculative types**: Only types with actual callers remain
6. **No redundant layers**: Direct path from provider → client → SDK
7. **Provider still works**: `complete()` streams events correctly

---

## Execution Order

Execute changes 1-7 IN ORDER. Each builds on the previous.
After EACH change, run verification. Do NOT proceed if tests fail.

**This is aggressive surgery. Go slow. Verify constantly.**
