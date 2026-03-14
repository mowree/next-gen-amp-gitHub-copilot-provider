# Semantic Code Analysis — LSP/Pyright Deep Review

**Date:** 2026-03-14  
**Tool:** Pyright (via LSP)  
**Scope:** `amplifier_module_provider_github_copilot/` — all modules  

---

## 1. LSP Environment

Pyright resolved and returned diagnostics successfully. `amplifier_core` is an external
dependency not installed in the Pyright analysis workspace, so all symbols imported from
it are flagged `reportMissingImports`. This is expected — not a real defect. All other
findings below are real.

---

## 2. Diagnostic Summary by File

| File | Errors | Warnings | Notes |
|------|--------|----------|-------|
| `provider.py` | 4 | 1 | 3 are `amplifier_core` unresolved; 1 real |
| `error_translation.py` | 4 | 1 | **3 real `reportOptionalCall` bugs** |
| `streaming.py` | 2 | 1 | Both `amplifier_core` unresolved |
| `sdk_adapter/client.py` | 1 | 1 | 1 real; 4 hints (unused params) |
| `tool_parsing.py` | 1 | 0 | `amplifier_core` unresolved only |

### 2.1 Real Errors — `error_translation.py` (lines 337–371)

**Finding: `reportOptionalCall` — `KERNEL_ERROR_MAP.get()` result called without None guard**

```python
# Line 324
error_class = KERNEL_ERROR_MAP.get(mapping.kernel_error, ProviderUnavailableError)

# Lines 336–350
if error_class is InvalidToolCallError:
    kernel_error = error_class(...)   # Pyright: Object of type "None" cannot be called
else:
    kernel_error = error_class(...)   # Pyright: Object of type "None" cannot be called

# Lines 365–371 (default path)
default_class = KERNEL_ERROR_MAP.get(config.default_error, ProviderUnavailableError)
kernel_error = default_class(...)     # Pyright: Object of type "None" cannot be called
```

**Root cause:** `dict.get(key, default)` has type `V | None` when Pyright cannot prove
`default` is non-None. The default argument `ProviderUnavailableError` is itself typed
as `type[LLMError]`, but Pyright infers the return as `type[LLMError] | None` because
the map value type is `type[LLMError]` and the key might not exist.

**Runtime impact:** None — the dict always has all 15 error classes and the default
covers the fallback. But Pyright cannot verify this statically.

**Fix:** Use `cast()` or an explicit `or ProviderUnavailableError` guard:
```python
error_class = KERNEL_ERROR_MAP.get(mapping.kernel_error) or ProviderUnavailableError
```

### 2.2 Real Error — `provider.py` (lines 250, 259, 274)

**Finding: Deferred imports of `ProviderUnavailableError` and `LLMError` inside function body**

```python
# Lines 250, 259
from .error_translation import ProviderUnavailableError
# Line 274
from .error_translation import LLMError
```

These are inside the module-level `complete()` async generator. Pyright flags them as
`reportAttributeAccessIssue` because `amplifier_core` isn't resolved, but the structural
issue is the deferred import pattern itself. These symbols are already imported at the
top of `error_translation.py` — they should be imported at the top of `provider.py`
to avoid repeated import overhead per call and to make dependencies explicit.

**Note:** This likely exists to avoid a circular import. The actual circular dependency
risk should be investigated before moving these to module level.

### 2.3 Real Error — `sdk_adapter/client.py` (line 204)

```python
from ..error_translation import ProviderUnavailableError  # inside except ImportError block
```

Same pattern as above — deferred import. `ProviderUnavailableError` is already available
via the top-level import `from ..error_translation import ErrorConfig, ErrorMapping, translate_sdk_error`.
It should be added to that import list.

### 2.4 Hints — `sdk_adapter/client.py` (lines 37, 43)

Pyright reports 4 unused parameters as hints:

```python
async def deny(input_data: Any, invocation: Any) -> dict[str, str]:  # both unused
    return DENY_ALL

def deny_permission_request(request: Any, invocation: dict[str, str]) -> Any:  # both unused
```

These are callback signatures required by the SDK API. The parameters are intentionally
unused — the function always returns the same denial response regardless of input.
Convention fix: rename to `_input_data`, `_invocation`, `_request` (underscore prefix
signals intentionally unused). This is a style/lint issue, not a bug.

---

## 3. Call Graph Analysis

### 3.1 `GitHubCopilotProvider.complete()` — Two Execution Paths

```
GitHubCopilotProvider.complete(request, **kwargs)
│
├─ [Test path: sdk_create_fn injected]
│   └─ _complete_internal(request, config=..., sdk_create_fn=...)
│       └─ module-level complete(request, config=..., sdk_create_fn=...)  [async generator]
│           ├─ load_event_config()  → EventConfig from YAML
│           ├─ load_error_config()  → ErrorConfig from YAML
│           ├─ sdk_create_fn(session_config)  → SDKSession
│           ├─ session.register_pre_tool_use_hook(create_deny_hook())
│           ├─ session.send_message(prompt, tools)  [async iterator]
│           │   └─ translate_event(sdk_event, event_config)  → DomainEvent | None
│           └─ [finally] session.disconnect()
│
└─ [Real SDK path: no sdk_create_fn]
    └─ CopilotClientWrapper.session(model=model)  [asynccontextmanager]
        ├─ _get_client() → existing client OR lazy-init CopilotClient
        │   ├─ CopilotClient(options)  [with deny_permission_request hook]
        │   └─ client.start()
        ├─ client.create_session(session_config)  → sdk_session
        ├─ sdk_session.register_pre_tool_use_hook(create_deny_hook())
        ├─ yield sdk_session
        └─ [finally] sdk_session.disconnect()
    └─ sdk_session.send_and_wait({"prompt": ...})  → sdk_response
        └─ extract_response_content(sdk_response)  → str
            └─ DomainEvent(CONTENT_DELTA, {"text": content})
```

**Observation:** The test path uses `session.send_message()` (streaming); the real SDK
path uses `sdk_session.send_and_wait()` (blocking). These are semantically different
APIs. The test path yields events; the real path builds one synthetic `CONTENT_DELTA`
event. This asymmetry means test coverage with `sdk_create_fn` does NOT exercise the
real SDK API path.

### 3.2 Error Translation Call Graph

```
[any exception in complete()]
└─ translate_sdk_error(exc, error_config, provider="github-copilot", model=...)
    ├─ _matches_mapping(exc, mapping) for each mapping in config.mappings
    │   ├─ type(exc).__name__ in mapping.sdk_patterns
    │   └─ pattern.lower() in str(exc).lower()  ← string patterns
    ├─ KERNEL_ERROR_MAP.get(mapping.kernel_error, ProviderUnavailableError)
    ├─ _extract_retry_after(message)  [if extract_retry_after=True]
    ├─ _extract_context(message, mapping.context_extraction)  [F-036]
    └─ error_class(message, provider=..., model=..., retryable=..., retry_after=...)
        └─ kernel_error.__cause__ = exc
```

**Observation:** The `InvalidToolCallError` branch (lines 336–342) creates the error
without `retry_after`. All other error classes receive `retry_after`. This is
intentional per the comment "doesn't accept retry_after" but is not documented in
`InvalidToolCallError`'s interface contract.

### 3.3 `CopilotClientWrapper.session()` — Deny-at-Source Architecture

Two layers of denial run on every session:

| Layer | Registration Point | Mechanism |
|-------|--------------------|-----------|
| 1st (earliest) | `CopilotClient` options at `__init__` | `on_permission_request=deny_permission_request` |
| 2nd (session) | `session_config["on_permission_request"]` | same handler |
| 3rd (post-create) | `sdk_session.register_pre_tool_use_hook()` | async deny hook |

This triple-registration reflects SDK version drift (F-033 note in code) — different
SDK versions require different registration points.

---

## 4. Type Inference Findings

### 4.1 `GitHubCopilotProvider.complete()` — `request: Any`

The method signature takes `request: Any`, then uses `getattr()` for all field access.
No type narrowing occurs. Pyright infers all extracted values as `Any`. This is
intentional — the method must accept both `CompletionRequest` and kernel `ChatRequest`
(a type from `amplifier_core` that Pyright can't see). However, the `isinstance` check
on line 439 is the only type guard:

```python
if isinstance(request, CompletionRequest):
    internal_request = request
else:
    # All getattr() calls — fully untyped
    messages: list[Any] = getattr(request, "messages", [])
```

**Risk:** If the kernel changes `ChatRequest`'s field names, this silently degrades
(returns empty prompt) rather than raising a type error.

### 4.2 `SDKSession = Any` — Opaque Boundary Type

```python
# sdk_adapter/types.py
SDKSession = Any
```

The entire SDK session interface is typed as `Any`. Every call into `sdk_session` (e.g.,
`.send_and_wait()`, `.disconnect()`, `.register_pre_tool_use_hook()`) is unchecked.
Pyright emits `# type: ignore` suppression comments on these calls throughout
`client.py`. This is by design (SDK boundary isolation) but means type errors at the
SDK interface surface are invisible.

### 4.3 `StreamingAccumulator.to_chat_response()` — Deferred Import Types

```python
def to_chat_response(self) -> "ChatResponse":  # string annotation
    from amplifier_core import (ChatResponse, TextBlock, ThinkingBlock, ToolCall, Usage)
```

The return type is a forward reference string `"ChatResponse"` because `ChatResponse`
is only available after the deferred import. This is correct Python, but Pyright treats
the return type as partially unknown since `amplifier_core` doesn't resolve. The
`content: list[TextBlock | ThinkingBlock]` is passed with `# type: ignore[arg-type]`
on line 162 — indicating a known mismatch between the local type and `ChatResponse`'s
actual constructor signature.

---

## 5. Potentially Dead / Unreferenced Code

### 5.1 `complete_and_collect()` — Module-Level Convenience Function

```python
async def complete_and_collect(request, *, config=None, sdk_create_fn=None) -> AccumulatedResponse:
```

This function is **not called anywhere in `GitHubCopilotProvider`**. The provider class
uses `StreamingAccumulator` directly. `complete_and_collect()` wraps the module-level
`complete()` generator, which is itself only reached via `_complete_internal()` on the
test path.

**Likely status:** Used in tests or by external callers directly importing the module.
Verify with: `grep -r "complete_and_collect" tests/`

### 5.2 `GitHubCopilotProvider._complete_fn` — Never Set After Init

```python
# provider.py line 360
self._complete_fn: SDKCreateFn | None = None
```

This attribute is initialized to `None` in `__init__` and checked in `complete()`:

```python
sdk_create_fn = kwargs.get("sdk_create_fn") or self._complete_fn
```

But `_complete_fn` is never set anywhere in the class. There is no setter, no test
that injects via this attribute, and no public API for setting it. It is effectively
dead — the only injection mechanism is the `sdk_create_fn` kwarg.

**Likely status:** Left over from an earlier design where the SDK factory was injected
at construction time. Should be removed or documented.

### 5.3 `AccumulatedResponse` Dataclass — Returned But Rarely Consumed

`StreamingAccumulator.get_result()` returns `AccumulatedResponse`, but the main
execution paths always call `to_chat_response()` directly. `get_result()` is only
useful if a caller wants the raw domain-layer accumulated state before kernel
conversion. Check whether any tests or callers use it.

### 5.4 `SessionConfig` from `sdk_adapter/types.py` — Partial Usage

```python
@dataclass
class SessionConfig:
    model: str
    system_prompt: str | None = None
    max_tokens: int | None = None
```

`SessionConfig` is imported in `provider.py` and used in the module-level `complete()`
function (line 241: `SessionConfig(model=request.model or "gpt-4")`). However, it is
**not used** in `CopilotClientWrapper.session()` — that function takes `model: str`
and `system_message: str` directly, building its own `session_config: dict[str, Any]`.

The `system_prompt` and `max_tokens` fields on `SessionConfig` have no code path that
propagates them to the SDK. If the legacy `complete()` module-level function is
deprecated, `SessionConfig` becomes fully dead.

---

## 6. Import Graph

```
provider.py
├── amplifier_core  [ChatResponse, ModelInfo, ProviderInfo, ToolCall]
├── error_translation  [ErrorConfig, load_error_config, translate_sdk_error]
│   └── amplifier_core.llm_errors  [15 error types]
│   └── yaml
├── sdk_adapter.client  [CopilotClientWrapper, create_deny_hook]
│   └── error_translation  [ErrorConfig, ErrorMapping, translate_sdk_error]
│   └── yaml
│   └── copilot  [CopilotClient — lazy import, SDK boundary]
├── sdk_adapter.types  [SDKSession, SessionConfig]
├── streaming  [AccumulatedResponse, DomainEvent, DomainEventType, EventConfig,
│              StreamingAccumulator, load_event_config, translate_event]
│   └── amplifier_core  [ChatResponse — TYPE_CHECKING only]
│   └── yaml
└── tool_parsing  [parse_tool_calls]
    └── amplifier_core  [ToolCall]
```

**Potential circular import:** `provider.py` imports from `error_translation`. The
module-level `complete()` function defers `from .error_translation import ProviderUnavailableError`
inside the function body. This suggests a possible circular import was observed or
feared at some point, but examination of `error_translation.py` shows it has no imports
from `provider.py`. The deferred import appears to be unnecessary defensive coding.

**SDK isolation is clean:** Only `sdk_adapter/client.py` imports from `copilot` (the
real SDK), and only lazily inside `CopilotClientWrapper.session()`. The contract
`sdk-boundary.md` is enforced structurally.

---

## 7. Structural Observations

### 7.1 Dual `complete()` Names

There are two `complete()` functions with the same name:
1. **Module-level** `complete()` — async generator, test/legacy path
2. **`GitHubCopilotProvider.complete()`** — async method, kernel interface

This naming collision is not a Python error (different scopes) but creates
confusion when reading call stacks or searching the codebase.

### 7.2 `content` Variable Shadowing in `GitHubCopilotProvider.complete()`

```python
# Line 445
content: Any = getattr(msg, "content", "")  # outer loop variable
# ...
# Line 488
content = extract_response_content(sdk_response)  # reuse of same name, different branch
```

These are in separate `if/else` branches so there's no actual shadowing bug, but the
reuse of `content` as a variable name in both branches of a large function body can
mislead readers.

### 7.3 `_load_error_config_once()` in `client.py` — Partial Duplication

`client.py` has its own `_load_error_config_once()` that partially reimplements the
`load_error_config()` logic from `error_translation.py`, adding `importlib.resources`
as a first-try path. The `ContextExtraction` handling present in `error_translation.load_error_config()`
is absent in the client's version — context extraction patterns in `errors.yaml` will
be silently dropped when loaded via the `importlib.resources` path.

---

## 8. Summary of Actionable Findings

| Priority | Location | Issue | Action |
|----------|----------|-------|--------|
| HIGH | `error_translation.py:324,337,344,366` | `reportOptionalCall` — `.get()` return called without None guard | Add `or ProviderUnavailableError` fallback or use `cast()` |
| MEDIUM | `sdk_adapter/client.py:80–103` | `_load_error_config_once()` omits `context_extraction` from F-036 | Sync with `load_error_config()` or delegate to it |
| MEDIUM | `provider.py:360` | `_complete_fn` attribute never set — dead code | Remove or document intended use |
| MEDIUM | `provider.py:250,259,274` / `client.py:204` | Deferred imports of already-available symbols | Move to module-level imports (verify no circular import) |
| LOW | `sdk_adapter/client.py:37,43` | Unused callback parameters | Prefix with `_` |
| LOW | `provider.py` | Dual `complete()` name (module + method) | Rename module-level to `_execute_complete()` or similar |
| INFO | `provider.py:295` | `complete_and_collect()` — verify if still used | `grep -r "complete_and_collect" tests/` |
| INFO | `sdk_adapter/types.py:SessionConfig` | `system_prompt`/`max_tokens` fields never propagated to SDK | Remove fields or wire them through |
