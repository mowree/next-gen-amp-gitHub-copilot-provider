# Amplifier Ecosystem Compliance Review

**Date**: 2026-03-14  
**Reviewer**: amplifier-expert (Amplifier Ecosystem Specialist)  
**Project**: `amplifier-module-provider-github-copilot`  
**Kernel Reference**: `reference-only/amplifier-core/` (v1.0.7)  
**Vision Reference**: `mydocs/debates/GOLDEN_VISION_V2.md` (v2.1)

---

## Summary Verdict

| # | Requirement | Rating | Notes |
|---|------------|--------|-------|
| 1 | Provider Protocol (5 methods) | **COMPLIANT** | All 4 methods + 1 property correctly implemented |
| 2 | Event Emission | **PARTIAL** | Internal domain events work; no kernel hook emission |
| 3 | Error Types | **COMPLIANT** | Uses kernel `amplifier_core.llm_errors.*` types |
| 4 | Session Lifecycle | **COMPLIANT** | Deny+Destroy pattern correctly implemented |
| 5 | Tool Handling | **COMPLIANT** | Correct async iteration, proper ToolCall type |
| 6 | Context Management | **COMPLIANT** | No context leakage; proper delegation |
| 7 | Module Packaging | **COMPLIANT** | Entry points, naming, build system all correct |

**Overall: COMPLIANT (with one advisory)**

---

## 1. Provider Protocol — COMPLIANT

### What the Kernel Requires

From `amplifier_core.interfaces.Provider` (Protocol class):

```python
@runtime_checkable
class Provider(Protocol):
    @property
    def name(self) -> str: ...
    def get_info(self) -> ProviderInfo: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

### What the Provider Implements

| Method | Kernel Signature | Provider Signature | Match |
|--------|-----------------|-------------------|-------|
| `name` | `@property → str` | `@property → str` (returns `"github-copilot"`) | ✅ |
| `get_info()` | `→ ProviderInfo` | `→ ProviderInfo` (from `amplifier_core`) | ✅ |
| `list_models()` | `async → list[ModelInfo]` | `async → list[ModelInfo]` (from `amplifier_core`) | ✅ |
| `complete()` | `async (ChatRequest, **kwargs) → ChatResponse` | `async (Any, **kwargs) → ChatResponse` | ✅ |
| `parse_tool_calls()` | `(ChatResponse) → list[ToolCall]` | `(Any) → list[ToolCall]` | ✅ |

**Details:**

- **`name`**: Returns `"github-copilot"` as a property. Correct. ✅
- **`get_info()`**: Returns `ProviderInfo` imported from `amplifier_core.models`. Fields (`id`, `display_name`, `credential_env_vars`, `capabilities`, `defaults`, `config_fields`) all populated from YAML config. ✅
- **`list_models()`**: Returns `list[ModelInfo]` from `amplifier_core.models`. Fields (`id`, `display_name`, `context_window`, `max_output_tokens`, `capabilities`, `defaults`) correctly populated. ✅
- **`complete()`**: Accepts `request: Any` and `**kwargs`, returns `ChatResponse`. The `Any` type annotation is slightly looser than the kernel's `ChatRequest`, but this is structurally compatible — the method internally handles both `CompletionRequest` (internal) and kernel `ChatRequest` objects. The `**kwargs` pattern matches kernel contract. ✅
- **`parse_tool_calls()`**: Returns `list[ToolCall]` using kernel `ToolCall` from `amplifier_core.message_models`. Uses `arguments` field (not `input`). Delegates to `tool_parsing` module. ✅

**Type Import Verification:**
```python
# provider.py line 33
from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
```
All four kernel types imported from `amplifier_core`. No local dataclass definitions. ✅

### Advisory

The `complete()` method signature uses `request: Any` instead of `request: ChatRequest`. This works because Python's Protocol uses structural subtyping and the method internally handles both types. However, for strict pyright compliance and documentation clarity, `ChatRequest` would be preferable as the type annotation. This is cosmetic — runtime behavior is correct.

---

## 2. Event Emission — PARTIAL

### What the Kernel Provides

From `amplifier_core.events`:
```
PROVIDER_REQUEST, PROVIDER_RESPONSE, PROVIDER_RETRY, PROVIDER_ERROR,
PROVIDER_THROTTLE, CONTENT_BLOCK_START, CONTENT_BLOCK_DELTA, CONTENT_BLOCK_END,
THINKING_DELTA, THINKING_FINAL
```

### What the Provider Does

The provider implements a **two-tier event system**:

**Tier 1 — Internal Domain Events** (implemented): ✅
- `DomainEventType.CONTENT_DELTA` — text/thinking deltas from SDK
- `DomainEventType.TOOL_CALL` — tool call extraction
- `DomainEventType.USAGE_UPDATE` — token usage
- `DomainEventType.TURN_COMPLETE` — completion signal
- `DomainEventType.SESSION_IDLE` — session idle
- `DomainEventType.ERROR` — error events

These are config-driven via `config/events.yaml` with BRIDGE/CONSUME/DROP classification. ✅

**Tier 2 — Kernel Hook Events** (not implemented): ⚠️

The provider does NOT emit kernel events via `coordinator.emit()` or `hooks.emit()`. Events like `PROVIDER_REQUEST`, `PROVIDER_RESPONSE`, `PROVIDER_ERROR` are not emitted to the kernel's hook system.

### Assessment

This is rated **PARTIAL** because:
- The internal event translation layer is well-designed and config-driven
- However, the kernel's observability contract expects providers to emit `PROVIDER_*` events so hooks (logging, metrics, approval) can observe provider behavior
- The orchestrator typically handles `PROVIDER_REQUEST`/`PROVIDER_RESPONSE` emission, but `PROVIDER_ERROR` and streaming events (`CONTENT_BLOCK_DELTA`, `THINKING_DELTA`) are traditionally provider-emitted

**Impact**: Hooks registered for `PROVIDER_ERROR`, `CONTENT_BLOCK_DELTA`, etc. won't fire. This means logging hooks, streaming UI hooks, and metrics hooks have no visibility into this provider's internal behavior.

**Note**: This is common in early-stage providers. The kernel's Provider Protocol does not *require* event emission (it's not in the Protocol class). It's a behavioral expectation documented in `docs/contracts/PROVIDER_CONTRACT.md`, not enforced via typing. The Golden Vision V2 acknowledges this is Phase 2 work.

---

## 3. Error Types — COMPLIANT

### What the Kernel Requires

From `amplifier_core.llm_errors`:
```
LLMError (base)
├── AuthenticationError
├── RateLimitError
│   └── QuotaExceededError
├── LLMTimeoutError
├── ContentFilterError
├── NotFoundError
├── ProviderUnavailableError
│   └── NetworkError
├── StreamError
├── AbortError
├── InvalidToolCallError
├── ConfigurationError
├── AccessDeniedError
├── ContextLengthError
└── InvalidRequestError
```

### What the Provider Does

**Import verification** (`error_translation.py` lines 37-54):
```python
from amplifier_core.llm_errors import (
    AbortError, AccessDeniedError, AuthenticationError, ConfigurationError,
    ContentFilterError, ContextLengthError, InvalidRequestError,
    InvalidToolCallError, LLMError, LLMTimeoutError, NetworkError,
    NotFoundError, ProviderUnavailableError, QuotaExceededError,
    RateLimitError, StreamError,
)
```

All 15 kernel error types imported. ✅

**KERNEL_ERROR_MAP** (lines 60-76): Maps config string names to kernel classes. All 15 types registered. ✅

**Config-driven translation** (`config/errors.yaml`):

| SDK Pattern | Kernel Error | Retryable | Correct? |
|------------|-------------|-----------|----------|
| `AuthenticationError`, `InvalidTokenError` | `AuthenticationError` | false | ✅ |
| `RateLimitError` | `RateLimitError` | true | ✅ |
| `QuotaExceededError` | `QuotaExceededError` | false | ✅ |
| `TimeoutError` | `LLMTimeoutError` | true | ✅ |
| `ContentFilterError`, `SafetyError` | `ContentFilterError` | false | ✅ |
| `ConnectionError`, `ProcessExitedError` | `NetworkError` | true | ✅ |
| `ModelNotFoundError` | `NotFoundError` | false | ✅ |
| `ContextLengthError` | `ContextLengthError` | false | ✅ |
| `StreamError` | `StreamError` | true | ✅ |
| `InvalidToolCallError` | `InvalidToolCallError` | false | ✅ |
| `ConfigurationError` | `ConfigurationError` | false | ✅ |
| `CircuitBreakerError` | `ProviderUnavailableError` | false | ✅ |
| Default | `ProviderUnavailableError` | true | ✅ |

**Retryability alignment with kernel defaults:**

| Kernel Error | Kernel Default | Config Value | Match |
|-------------|---------------|-------------|-------|
| `AuthenticationError` | `retryable=False` | `false` | ✅ |
| `RateLimitError` | `retryable=True` | `true` | ✅ |
| `QuotaExceededError` | `retryable=False` | `false` | ✅ |
| `LLMTimeoutError` | `retryable=True` | `true` | ✅ |
| `ContentFilterError` | `retryable=False` | `false` | ✅ |
| `NetworkError` | `retryable=True` (inherits `ProviderUnavailableError`) | `true` | ✅ |
| `NotFoundError` | `retryable=False` | `false` | ✅ |
| `StreamError` | `retryable=True` | `true` | ✅ |
| `InvalidToolCallError` | `retryable=False` | `false` | ✅ |
| `ProviderUnavailableError` | `retryable=True` | `true` (default) | ✅ |

**Exception chaining**: `kernel_error.__cause__ = exc` — preserves original. ✅  
**Provider attribution**: `provider="github-copilot"` set on all errors. ✅  
**No custom error hierarchy**: Confirmed — no `CopilotAuthError` or similar. Golden Vision V2.1 correction E5 applied. ✅

**Special handling for `InvalidToolCallError`**: Correctly detected — this kernel error has a different `__init__` signature (no `retry_after` param). Provider handles this with a special branch. ✅

---

## 4. Session Lifecycle — COMPLIANT

### Deny+Destroy Pattern

The Golden Vision V2 mandates:
1. Every SDK session gets a `preToolUse` deny hook
2. Sessions are ephemeral: create, use once, destroy
3. This is NEVER configurable

**Implementation verification:**

**Deny hook** (`sdk_adapter/client.py`):
```python
DENY_ALL = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty - tools executed by kernel only",
}
```
- `create_deny_hook()` creates async deny function ✅
- `deny_permission_request()` denies at permission-request level (F-033) ✅
- Both hooks registered on every session creation (lines 241-243) ✅

**Ephemeral sessions** (`CopilotClientWrapper.session()`):
- Sessions created via `async with` context manager ✅
- `create_session()` → use → `disconnect()` in `finally` block ✅
- No session reuse or state accumulation ✅

**Internal `complete()` function** (`provider.py` lines 244-292):
- Creates session per call ✅
- Registers deny hook if `register_pre_tool_use_hook` exists ✅
- Destroys session in `finally` block via `disconnect()` ✅
- No cross-call state ✅

**Non-configurability**: Deny+Destroy has no YAML knob. It's hardcoded in Python mechanism code. ✅

### SDK Containment

- All SDK imports confined to `sdk_adapter/client.py` ✅
- `sdk_adapter/types.py` defines domain types (no SDK imports) ✅
- `SDKSession = Any` — opaque type alias ✅
- No SDK types leak into `provider.py`, `streaming.py`, or `error_translation.py` ✅

---

## 5. Tool Handling — COMPLIANT

### What the Kernel Requires

From `interfaces.py`:
```python
def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

Where `ToolCall` (from `message_models.py`):
```python
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]  # NOT "input"
```

### What the Provider Does

**`tool_parsing.py`**:
- Imports `ToolCall` from `amplifier_core` (line 22) ✅
- Returns `list[ToolCall]` ✅
- Uses `arguments` field (not `input`) — Golden Vision V2.1 correction E3 applied ✅
- Handles empty/missing tool_calls → returns `[]` ✅
- Handles JSON string arguments → `json.loads()` ✅
- Preserves tool call IDs ✅
- F-037: Warns on empty arguments (hallucination detection) ✅

**Provider delegation** (`provider.py` line 532):
```python
def parse_tool_calls(self, response: Any) -> list[ToolCall]:
    return parse_tool_calls(response)
```
Clean delegation to module. ✅

### Tool Capture (Not Execution)

The provider captures tool calls via streaming events but NEVER executes them:
- `DomainEventType.TOOL_CALL` events are bridged from SDK ✅
- `DENY_ALL` hook prevents SDK from executing tools ✅
- Tool calls are returned in `ChatResponse.tool_calls` for orchestrator processing ✅

---

## 6. Context Management — COMPLIANT

### What the Kernel Requires

Providers should NOT manage context. Context is the orchestrator's domain (via `ContextManager` protocol).

### What the Provider Does

- No context storage or management ✅
- No conversation history tracking ✅
- Each `complete()` call is stateless ✅
- Messages extracted from `ChatRequest.messages` per call, not accumulated ✅
- Provider does not import or reference `ContextManager` ✅

The provider correctly treats each request as independent, leaving context management to the orchestrator. This aligns with the Golden Vision V2 principle: "Translation, Not Framework."

---

## 7. Module Packaging — COMPLIANT

### pyproject.toml

| Requirement | Expected | Actual | Match |
|------------|----------|--------|-------|
| Project name | `amplifier-module-provider-*` | `amplifier-module-provider-github-copilot` | ✅ |
| Entry point group | `amplifier.modules` | `[project.entry-points."amplifier.modules"]` | ✅ |
| Entry point name | `provider-github-copilot` | `provider-github-copilot = "amplifier_module_provider_github_copilot:mount"` | ✅ |
| Build system | Any PEP 517 | `hatchling` | ✅ |
| Python version | `>=3.11` | `>=3.11` | ✅ |
| amplifier-core dep | Runtime provided | Listed in `[dev]` only, not in main deps | ✅ |

Golden Vision V2.1 corrections E6 (naming) and E7 (entry points) both applied. ✅

### `__init__.py` Module Metadata

```python
__amplifier_module_type__ = "provider"
```
Module type declaration present. ✅

### `mount()` Function

```python
async def mount(coordinator, config=None) -> CleanupFn | None:
```
- Accepts `coordinator` and optional `config` ✅
- Creates provider instance ✅
- Mounts via `coordinator.mount("providers", provider, name="github-copilot")` ✅
- Returns cleanup callable ✅
- Graceful degradation on failure (returns `None`, logs error) ✅

### SDK Dependency Guard

```python
if not _os.environ.get("SKIP_SDK_CHECK"):
    try:
        _pkg_version("github-copilot-sdk")
    except _PkgNotFoundError:
        raise ImportError(...)
```
Eager check prevents silent discovery failure. ✅

---

## Cross-Cutting Observations

### Three-Medium Architecture Compliance

| Medium | Expected | Actual | Status |
|--------|----------|--------|--------|
| Python (mechanism) | ~670 lines new code | ~1,300 lines across 7 files | ⚠️ Higher than target |
| YAML (policy) | ~160 lines config | ~185 lines across 4 files | ✅ Close to target |
| Markdown (contracts) | ~400 lines | 8 contract files in `contracts/` | ✅ |

The Python code is ~2× the Golden Vision target, largely due to the `provider.py` orchestrator being 532 lines (target: 120). This includes `CompletionRequest`, `CompletionConfig`, `ProviderConfig` dataclasses, the `extract_response_content()` utility, and both real-SDK and test-injection paths in `complete()`. This is acceptable for a working implementation but should be tracked as technical debt for Phase 1 refactoring.

### Config-Driven Architecture

All tunable policies are externalized to YAML:
- Error mappings → `config/errors.yaml` ✅
- Event classification → `config/events.yaml` ✅
- Model catalog → `config/models.yaml` ✅
- Retry policy → `config/retry.yaml` (present but not consumed by code yet) ⚠️

### Kernel Type Usage Summary

| Kernel Type | Module | Imported From | Used Correctly |
|------------|--------|--------------|---------------|
| `ProviderInfo` | `provider.py` | `amplifier_core` | ✅ |
| `ModelInfo` | `provider.py` | `amplifier_core` | ✅ |
| `ChatResponse` | `provider.py`, `streaming.py` | `amplifier_core` | ✅ |
| `ToolCall` | `provider.py`, `tool_parsing.py` | `amplifier_core` | ✅ |
| `TextBlock` | `streaming.py` | `amplifier_core` | ✅ |
| `ThinkingBlock` | `streaming.py` | `amplifier_core` | ✅ |
| `Usage` | `streaming.py` | `amplifier_core` | ✅ |
| `LLMError` + 14 subtypes | `error_translation.py` | `amplifier_core.llm_errors` | ✅ |

No local type definitions that shadow kernel types. ✅

---

## Recommendations

### Priority 1 — Emit Kernel Events (Partial → Compliant)

Add `coordinator.emit()` calls for:
- `PROVIDER_REQUEST` before SDK call
- `PROVIDER_RESPONSE` after SDK response
- `PROVIDER_ERROR` on translated errors
- `CONTENT_BLOCK_DELTA` for streaming deltas

This enables the kernel's observability infrastructure (logging hooks, metrics hooks, streaming UI hooks) to work with this provider.

### Priority 2 — Consume `config/retry.yaml`

The retry config file exists but is not consumed by any Python code. Either wire it into the completion lifecycle or remove it to avoid config-code drift (risk C2 from Golden Vision).

### Priority 3 — Tighten `complete()` Type Signature

Change `request: Any` to `request: ChatRequest` in `GitHubCopilotProvider.complete()`. The internal `CompletionRequest` path can be handled via a separate private method.

### Priority 4 — Reduce `provider.py` Size

At 532 lines, `provider.py` exceeds the 400-line soft cap. Consider extracting:
- `ProviderConfig` + `_load_models_config()` → `config.py`
- `extract_response_content()` → `sdk_adapter/types.py`
- `complete()` module-level function → `completion.py`

---

## Conclusion

This provider is **ecosystem-compliant** with Amplifier's kernel contracts. All five Provider Protocol methods are correctly implemented with kernel types. Error translation uses the kernel hierarchy exclusively (no custom error classes). The Deny+Destroy pattern is correctly enforced as non-configurable mechanism. Module packaging follows ecosystem conventions with proper entry points.

The one area rated PARTIAL (event emission) is a known gap that doesn't break functionality — it reduces observability. The Golden Vision V2 roadmap places this in Phase 2. The provider is ready for integration testing with the Amplifier kernel.

---

*Reviewed against: `amplifier_core` v1.0.7, `interfaces.Provider` Protocol, `llm_errors.*` hierarchy, `message_models.*` types, `models.*` types, `events.*` constants.*
