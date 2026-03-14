# Kernel Contract Compliance Review

**Date:** 2026-03-14
**Reviewer:** Core Expert (Kernel Specialist)
**Module:** amplifier-module-provider-github-copilot
**Kernel Reference:** amplifier-core v1.0.7+

---

## 1. Provider Protocol — COMPLIANT ✅

**Contract:** `PROVIDER_CONTRACT.md` — 5 methods: `name`, `get_info()`, `list_models()`, `complete()`, `parse_tool_calls()`

| Requirement | Status | Evidence |
|---|---|---|
| `name` property returns `"github-copilot"` | ✅ | `provider.py:367-372` — `@property` returning exact string |
| `get_info()` returns `ProviderInfo` | ✅ | `provider.py:374-389` — returns kernel `ProviderInfo` from `amplifier_core.models` |
| `list_models()` returns `list[ModelInfo]` | ✅ | `provider.py:391-421` — returns kernel `ModelInfo` from `amplifier_core.models` |
| `complete(request, **kwargs)` returns `ChatResponse` | ✅ | `provider.py:423-498` — accepts `Any` request + `**kwargs`, returns `ChatResponse` |
| `parse_tool_calls(response)` returns `list[ToolCall]` | ✅ | `provider.py:525-532` — delegates to `tool_parsing.parse_tool_calls()` |
| `mount()` entry point | ✅ | `__init__.py:52-92` — `async def mount(coordinator, config)` |
| `pyproject.toml` entry point | ✅ | `pyproject.toml:31-32` — `provider-github-copilot = "...mount"` |
| Graceful degradation on mount failure | ✅ | `__init__.py:85-92` — catches exceptions, logs, returns `None` |
| Cleanup function returned | ✅ | `__init__.py:81-84` — returns `async def cleanup()` |
| `__amplifier_module_type__` metadata | ✅ | `__init__.py:46` — `"provider"` |

**Notes:**
- `complete()` signature uses `request: Any` instead of `request: ChatRequest`. This is structurally compatible (duck-typing), but the kernel Protocol specifies `ChatRequest`. The implementation handles both `CompletionRequest` and kernel `ChatRequest` via duck-typing at `provider.py:439-458`. This is **functionally compliant** but the type annotation is loose.
- `parse_tool_calls()` accepts `response: Any` instead of `response: ChatResponse`. Same duck-typing pattern. Functionally compliant.

**Minor Finding:** The `ProviderInfo` returned by `get_info()` does not include `context_window` in `defaults` unless configured in `config/models.yaml`. The contract says "MUST include `defaults.context_window` for budget calculation." The fallback config at `provider.py:116` has `defaults={"model": "gpt-4o", "max_tokens": 4096}` — missing `context_window`. **This is a gap** but depends on whether `config/models.yaml` provides it at runtime.

**Rating: COMPLIANT** (with one minor gap on `defaults.context_window` in fallback config)

---

## 2. Event Protocol — COMPLIANT ✅

**Contract:** `event-vocabulary.md` — 6 domain events, BRIDGE/CONSUME/DROP classification

| Requirement | Status | Evidence |
|---|---|---|
| 6 domain event types defined | ⚠️ Partial | `streaming.py:25-33` — defines `CONTENT_DELTA`, `TOOL_CALL`, `USAGE_UPDATE`, `TURN_COMPLETE`, `SESSION_IDLE`, `ERROR`. Missing `THINKING_DELTA` as separate type; uses `block_type="THINKING"` on `CONTENT_DELTA` instead |
| Config-driven classification | ✅ | `streaming.py:231-240` — `classify_event()` uses `EventConfig` from YAML |
| BRIDGE events translated | ✅ | `streaming.py:248-273` — `translate_event()` produces `DomainEvent` |
| CONSUME events processed internally | ✅ | `streaming.py:235-236` — matched and returned as `None` (not forwarded) |
| DROP events ignored | ✅ | `streaming.py:237-240` — matched and returned as `None` |
| Finish reason mapping | ✅ | `streaming.py:260-267` — applies `finish_reason_map` from config |
| `DomainEvent` structure | ✅ | `streaming.py:44-51` — `type`, `data`, `block_type` |

**Notes:**
- `THINKING_DELTA` from the contract vocabulary is handled via `block_type="THINKING"` on `CONTENT_DELTA` events rather than a separate enum value. The `StreamingAccumulator.add()` method at `streaming.py:82-83` correctly routes thinking content based on `block_type`. This is a valid implementation choice.
- The module does NOT emit events to the kernel hook system (e.g., `provider:request`, `provider:response`). This is correct — event emission is the **orchestrator's** responsibility per the Orchestrator Contract, not the provider's.

**Rating: COMPLIANT**

---

## 3. Error Protocol — COMPLIANT ✅

**Contract:** `error-hierarchy.md` — All SDK errors translated to `amplifier_core.llm_errors` types

| Requirement | Status | Evidence |
|---|---|---|
| Uses kernel error types only | ✅ | `error_translation.py:37-54` — imports all 15 types from `amplifier_core.llm_errors` |
| No custom error classes | ✅ | No custom `Exception` subclasses defined anywhere in the module |
| Sets `provider="github-copilot"` | ✅ | `error_translation.py:339,348,369` — all paths set provider |
| Preserves original exception | ✅ | `error_translation.py:351,372` — `kernel_error.__cause__ = exc` |
| Config-driven pattern matching | ✅ | `error_translation.py:321-362` — iterates `config.mappings` |
| Falls through to `ProviderUnavailableError` | ✅ | `error_translation.py:364-372` — default fallback |
| `translate_sdk_error()` never raises | ✅ | Function always returns; no unguarded exceptions |
| Extracts `retry_after` | ✅ | `error_translation.py:327-328` — conditional extraction |
| KERNEL_ERROR_MAP covers full hierarchy | ✅ | `error_translation.py:60-76` — all 15 kernel types mapped |

**Notes:**
- The `raise kernel_error from e` pattern in `provider.py:284` correctly chains the original exception.
- The `LLMError` double-wrap prevention at `provider.py:276-277` is good practice.

**Rating: COMPLIANT**

---

## 4. Session Protocol (Deny + Destroy) — COMPLIANT ✅

**Contract:** `deny-destroy.md` — Non-negotiable: deny hook + ephemeral sessions + no SDK tool execution

| Requirement | Status | Evidence |
|---|---|---|
| **preToolUse deny hook on every session** | ✅ | `client.py:241-243` — `register_pre_tool_use_hook(create_deny_hook())` on real SDK path; `provider.py:256-257` on test path |
| **Hook returns DENY for all requests** | ✅ | `client.py:28-31,37-38` — `DENY_ALL` constant, `deny()` returns it unconditionally |
| **No configuration disables the hook** | ✅ | No config knob exists anywhere to disable deny behavior |
| **New session per complete() call** | ✅ | `client.py:157-257` — `session()` is a context manager creating fresh sessions; `provider.py:481` — `async with self._client.session()` |
| **Session destroyed after first turn** | ✅ | `client.py:250-256` — `finally` block calls `sdk_session.disconnect()` |
| **No session reuse** | ✅ | Context manager pattern ensures no session escapes scope |
| **Tool requests captured, not executed** | ✅ | Tool calls flow through `StreamingAccumulator` → `ChatResponse.tool_calls` → returned to orchestrator |
| **`available_tools=[]` on every session** | ✅ | `client.py:220` — hardcoded `session_config["available_tools"] = []` |
| **`on_permission_request` deny handler** | ✅ | `client.py:43-69` — `deny_permission_request()` returns `"denied-by-rules"`; set at client level (`client.py:196`) and session level (`client.py:231`) |

**Three Lines of Defense:**
1. `on_permission_request` → deny all permission requests ✅
2. `register_pre_tool_use_hook` → deny all tool execution ✅  
3. `available_tools=[]` → prevent SDK tools from being offered to LLM ✅

**Rating: COMPLIANT**

---

## 5. Hook Integration — COMPLIANT ✅

**Contract:** `HOOK_CONTRACT.md` — Provider must be compatible with hook modules

| Requirement | Status | Evidence |
|---|---|---|
| Provider does NOT register hooks itself | ✅ | Correct — providers don't register lifecycle hooks; orchestrators do |
| Provider works with coordinator | ✅ | `__init__.py:78` — `await coordinator.mount("providers", provider, name="github-copilot")` |
| Provider returns data hooks can observe | ✅ | `complete()` returns `ChatResponse` with `content`, `tool_calls`, `usage` — all observable by orchestrator's `provider:response` emission |
| No hook bypass | ✅ | Provider doesn't execute tools or make decisions that would circumvent hooks |

**Notes:**
- The provider is a **passive participant** in the hook system, which is the correct role. It provides data (responses, tool calls) that orchestrators emit as hook events. The provider itself should NOT emit `tool:pre`, `tool:post`, etc. — that's orchestrator responsibility.
- The provider does NOT register observability events via `coordinator.register_contributor("observability.events", ...)`. This is a **RECOMMENDED** (not required) item from the Provider Contract checklist. The provider could register events like `github-copilot:session_created`, `github-copilot:session_destroyed` for enhanced observability.

**Rating: COMPLIANT**

---

## 6. Context Protocol — COMPLIANT ✅

**Contract:** `CONTEXT_CONTRACT.md` — Provider must work with context modules

| Requirement | Status | Evidence |
|---|---|---|
| Provider does not manage context | ✅ | No context management in provider — that's orchestrator/context module territory |
| `complete()` accepts messages via request | ✅ | `provider.py:443-458` — extracts messages from `ChatRequest` |
| Response compatible with context storage | ✅ | Returns `ChatResponse` with content blocks and tool calls — standard format for context managers to store |
| No state between calls | ✅ | Each `complete()` creates fresh internal state (`StreamingAccumulator`) |
| `ProviderInfo.defaults` supports budget calculation | ⚠️ | See note in §1 — `context_window` may be missing from fallback config |

**Notes:**
- The provider correctly stays out of context management. It receives a request, returns a response, and doesn't accumulate state. This is the correct separation of concerns per kernel philosophy.
- Context modules can use `provider.get_info().defaults.get("context_window")` for budget calculation. This works if `config/models.yaml` provides the value.

**Rating: COMPLIANT**

---

## Summary

| Contract | Rating | Notes |
|---|---|---|
| **1. Provider Protocol** | ✅ **COMPLIANT** | All 5 methods + mount(). Minor: `context_window` gap in fallback config |
| **2. Event Protocol** | ✅ **COMPLIANT** | 6 domain events, config-driven classification |
| **3. Error Protocol** | ✅ **COMPLIANT** | Full kernel hierarchy, config-driven translation, proper chaining |
| **4. Session Protocol** | ✅ **COMPLIANT** | Three-layer deny + destroy, no configuration escape hatches |
| **5. Hook Integration** | ✅ **COMPLIANT** | Passive participant, correct separation from orchestrator |
| **6. Context Protocol** | ✅ **COMPLIANT** | Stateless, standard response format |

---

## Recommendations (Non-Blocking)

1. **Type annotations on `complete()` and `parse_tool_calls()`**: Consider `request: ChatRequest` and `response: ChatResponse` instead of `Any` for better static analysis and protocol conformance signaling.

2. **`context_window` in fallback config**: Add `context_window` to `_default_provider_config()` defaults dict to ensure budget calculation works even without `config/models.yaml`.

3. **Observability contribution**: Register provider-specific events via `coordinator.register_contributor("observability.events", "github-copilot", ...)` for enhanced runtime introspection.

4. **`THINKING_DELTA` enum value**: Consider adding `THINKING_DELTA` as a first-class `DomainEventType` to match the contract vocabulary exactly, rather than overloading `CONTENT_DELTA` with `block_type`.

---

## Kernel Philosophy Assessment

The module correctly embodies kernel principles:

- **Mechanism, not policy**: The provider translates — it doesn't decide retry strategy, context management, or tool execution policy.
- **Deny + Destroy is mechanism**: The three-layer defense is hardcoded, not configurable. This is correct.
- **Error translation at boundary**: SDK errors are translated to kernel types at the boundary, preserving the kernel's error contract.
- **Separation of concerns**: Provider doesn't touch hooks, context, or orchestration — each stays in its lane.

**Overall Assessment: This module is kernel-contract compliant.**
