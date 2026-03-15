# Kernel Contract Compliance Review

**Date:** 2026-03-14
**Reviewer:** Core Expert (Kernel Specialist)
**Module:** amplifier-module-provider-github-copilot
**Kernel Reference:** amplifier-core v1.0.7+

---

## 1. Provider Protocol — NON-COMPLIANT ❌

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
| `ProviderInfo.defaults.context_window` present for budget calculation | ❌ | `provider.py:109-117` — fallback `_default_provider_config()` sets `defaults={"model": "gpt-4o", "max_tokens": 4096}` with no `context_window` |

**Notes:**
- `complete()` signature uses `request: Any` instead of `request: ChatRequest`. This is structurally compatible (duck-typing), but the kernel Protocol specifies `ChatRequest`. The implementation handles both `CompletionRequest` and kernel `ChatRequest` via duck-typing at `provider.py:439-458`.
- `parse_tool_calls()` accepts `response: Any` instead of `response: ChatResponse`. Same duck-typing pattern.
- The protocol surface is implemented correctly, but the fallback provider metadata still violates a MUST requirement for `defaults.context_window`.

**Rating: NON-COMPLIANT** (fallback metadata violates the MUST requirement for `defaults.context_window`)

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
- `THINKING_DELTA` from the contract vocabulary is handled via `block_type="THINKING"` on `CONTENT_DELTA` events rather than a separate enum value. The `StreamingAccumulator.add()` method at `streaming.py:82-83` correctly routes thinking content based on `block_type`.
- The module does NOT emit events to the kernel hook system (e.g., `provider:request`, `provider:response`). This is correct — event emission is the orchestrator's responsibility per the Orchestrator Contract, not the provider's.

**Rating: COMPLIANT**

---

## 3. Error Protocol — NON-COMPLIANT ❌

**Contract:** `error-hierarchy.md` — All SDK errors translated to `amplifier_core.llm_errors` types

| Requirement | Status | Evidence |
|---|---|---|
| Uses kernel error types only | ✅ | `error_translation.py:37-54` — imports all 15 types from `amplifier_core.llm_errors` |
| No custom error classes | ✅ | No custom `Exception` subclasses defined anywhere in the module |
| Test/injected completion path translates SDK errors | ✅ | `provider.py:272-284` — catches exceptions, skips double-wrapping for `LLMError`, calls `translate_sdk_error(...)`, then `raise kernel_error from e` |
| Real `GitHubCopilotProvider.complete()` SDK path translates `send_and_wait()` errors | ❌ | `provider.py:481-488` — `async with self._client.session(...)`, `await sdk_session.send_and_wait(...)`, and `extract_response_content(...)` execute with no local `try/except` and no call to `translate_sdk_error()` |
| Preserves original exception where translation occurs | ✅ | `error_translation.py:351,372` and `provider.py:284` — chaining preserved on translated paths |
| Config-driven pattern matching exists | ✅ | `error_translation.py:321-362` — iterates `config.mappings` |
| Falls through to `ProviderUnavailableError` | ✅ | `error_translation.py:364-372` — default fallback |
| `translate_sdk_error()` itself is safe | ✅ | Function returns translated kernel errors; no unguarded raise on reviewed path |
| No raw SDK exceptions escape `complete()` | ❌ | Violated on real path because `send_and_wait()` and response extraction are outside translation handling in `provider.py:481-488` |

**Notes:**
- My original review analyzed the module-level `complete()` path used for injected/test execution and incorrectly projected that behavior onto the real SDK path inside `GitHubCopilotProvider.complete()`.
- The real path introduced by the F-039/F-040 dual-path architecture is materially different: the test path translates exceptions, but the production SDK path does not.
- This violates the contract requirement that the provider MUST translate SDK errors into kernel error types.

**Rating: NON-COMPLIANT**

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
- The provider is a passive participant in the hook system, which is the correct role. It provides data that orchestrators emit as hook events.
- The provider does NOT register observability events via `coordinator.register_contributor("observability.events", ...)`. This is recommended, not required.

**Rating: COMPLIANT**

---

## 6. Context Protocol — NON-COMPLIANT ❌

**Contract:** `CONTEXT_CONTRACT.md` — Provider must work with context modules

| Requirement | Status | Evidence |
|---|---|---|
| Provider does not manage context | ✅ | No context management in provider — that's orchestrator/context module territory |
| `complete()` accepts messages via request | ✅ | `provider.py:443-458` — extracts messages from `ChatRequest` |
| Response compatible with context storage | ✅ | Returns `ChatResponse` with content blocks and tool calls — standard format for context managers to store |
| No state between calls | ✅ | Each `complete()` creates fresh internal state (`StreamingAccumulator`) |
| `ProviderInfo.defaults` supports budget calculation | ❌ | `provider.py:109-117` — fallback defaults omit required `context_window` |

**Notes:**
- The provider correctly stays out of context management.
- However, the fallback metadata is not sufficient for guaranteed budget calculation because `defaults.context_window` is a MUST, not an optional nicety.

**Rating: NON-COMPLIANT**

---

## 7. Summary

| Contract | Rating | Notes |
|---|---|---|
| **1. Provider Protocol** | ❌ **NON-COMPLIANT** | Method surface is correct, but fallback `defaults.context_window` violates a MUST |
| **2. Event Protocol** | ✅ **COMPLIANT** | Config-driven classification remains correct |
| **3. Error Protocol** | ❌ **NON-COMPLIANT** | Real SDK path leaks raw exceptions because it bypasses `translate_sdk_error()` |
| **4. Session Protocol** | ✅ **COMPLIANT** | Three-layer deny + destroy, no configuration escape hatches |
| **5. Hook Integration** | ✅ **COMPLIANT** | Passive participant, correct separation from orchestrator |
| **6. Context Protocol** | ❌ **NON-COMPLIANT** | Fallback metadata fails required budget field |

---

## 8. PRINCIPAL REVIEW AND AMENDMENTS

### Error Protocol — Corrected from ✅ COMPLIANT to ❌ NON-COMPLIANT

**Verified evidence:**
- The reviewed evidence in my original draft came from the module-level test/injected path at `provider.py:272-284`.
- The real production SDK path is `GitHubCopilotProvider.complete()` at `provider.py:481-488`.
- In that real path, `sdk_session.send_and_wait(...)` and `extract_response_content(...)` run without a surrounding `try/except` and without any call to `translate_sdk_error()`.
- I found no code in `GitHubCopilotProvider.complete()` that catches `send_and_wait()` failures before they escape.

**Root cause:**
- Dual-path architecture introduced in F-039/F-040.
- The injected/test path has error translation.
- The real SDK path does not.

**Remediation reference:**
- `specs/features/F-072-real-sdk-path-error-translation.md`

### `context_window` — Upgraded from “minor gap” to MUST violation

**Verified evidence:**
- Fallback provider metadata is defined in `_default_provider_config()` at `provider.py:109-117`.
- The fallback `defaults` dict is `{"model": "gpt-4o", "max_tokens": 4096}`.
- `context_window` is absent even though the provider contract requires `defaults.context_window` for budget calculation.

**Corrected assessment:**
- This is not a minor documentation gap or a runtime-dependent nicety.
- It is a MUST violation in the fallback metadata contract.

**Reviewer-requested remediation reference:**
- F-078 was cited in the principal feedback, but I could not verify an `F-078` spec file under `specs/features/` or an `F-078` entry in `STATE.yaml` in the current repo snapshot.

---

## 9. Recommendations

1. **Implement F-072**: Add error translation around the real SDK path in `GitHubCopilotProvider.complete()` so `send_and_wait()` and response extraction failures cannot leak raw SDK exceptions.
2. **Create or locate F-078**: The principal review references F-078 for `context_window` remediation, but no such spec was present in the current repo snapshot. Either create it or link the intended existing spec.
3. **Add `context_window` to fallback defaults**: `_default_provider_config()` should include the required budget field even when `config/models.yaml` is unavailable.
4. **Tighten type annotations**: Consider `request: ChatRequest` and `response: ChatResponse` instead of `Any` for better protocol conformance signaling.
5. **Optional observability contribution**: Register provider-specific events via `coordinator.register_contributor("observability.events", "github-copilot", ...)` for enhanced runtime introspection.

---

## 10. Kernel Philosophy Assessment

The module still aligns with kernel philosophy in its intended design:

- **Mechanism, not policy**: The provider translates rather than owning retry or orchestration policy.
- **Deny + Destroy is mechanism**: The three-layer defense is hardcoded, not configurable.
- **Separation of concerns**: Provider, hooks, context, and orchestration remain separated.

But intent is not enough for contract compliance.

**Overall Assessment: This module is not currently kernel-contract compliant due to the real SDK-path error translation gap and the missing fallback `defaults.context_window`.**