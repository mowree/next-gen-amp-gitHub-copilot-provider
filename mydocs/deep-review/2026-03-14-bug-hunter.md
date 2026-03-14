# Deep Review: Defect Analysis and Edge Cases
**Date:** 2026-03-14  
**Reviewer:** Bug Hunter Agent  
**Scope:** Full codebase — source, tests, config, contracts  
**Method:** Static analysis against GOLDEN_VISION_V2.md invariants + contract clauses

---

## Executive Summary

**18 potential defects found** across 4 severity levels. The most critical finding is a **silent false-negative in the architecture fitness tests** — the tests that guard the SDK boundary and deny-hook sovereignty scan a non-existent `src/` path, meaning they have never scanned a single file and always pass vacuously. Two additional correctness bugs exist in config loading paths. The rest are edge cases, weak assertions, and missing test coverage.

---

## CRITICAL Severity

### DEF-001 — Architecture Fitness Tests Scan Wrong Path (False Negatives)
**Files:** `tests/test_contract_deny_destroy.py:81`, `tests/test_sdk_client.py:191`  
**Severity:** CRITICAL — Contract enforcement is completely bypassed  

Both architecture fitness tests reference a non-existent `src/` subdirectory:

```python
# test_contract_deny_destroy.py:81
root = Path("src/amplifier_module_provider_github_copilot")

# test_sdk_client.py:191
src_root = Path("src/amplifier_module_provider_github_copilot")
```

The actual package is at `amplifier_module_provider_github_copilot/` (no `src/` prefix). When these paths don't exist, `root.glob("*.py")` yields **zero files**. Both tests pass unconditionally with zero assertions made.

**Impact:** The test `test_no_sdk_imports_outside_adapter` and `test_no_copilot_imports_in_domain_modules` — the primary enforcers of the SDK boundary contract (`deny-destroy:NoExecution:MUST:3`) — have **never scanned a single file**. An accidental `import copilot` in `error_translation.py` or `streaming.py` would not be caught.

**Evidence:** The tests pass even when pointing at a non-existent directory because `Path.glob()` returns an empty iterator, not an error.

**Fix:** Change to `Path("amplifier_module_provider_github_copilot")` in both tests.

---

### DEF-002 — `load_event_config` Crashes on Malformed YAML (Startup Killer)
**File:** `amplifier_module_provider_github_copilot/streaming.py:211-212`  
**Severity:** CRITICAL — Unhandled KeyError kills startup  

```python
for mapping in classifications.get("bridge", []):
    sdk_type = mapping["sdk_type"]          # KeyError if missing
    domain_type = DomainEventType[mapping["domain_type"]]  # KeyError if unknown value
```

Both accesses raise `KeyError` without try/except. Compare with `load_error_config()` which uses `.get()` with defaults throughout. If `events.yaml` has a bridge entry missing `sdk_type`, or if `domain_type` contains an unrecognized value (e.g., after a botched YAML edit), the entire provider fails to initialize — with a cryptic `KeyError` traceback, not a descriptive error.

**Contrast:** `load_error_config()` uses `mapping_data.get(...)` with defaults everywhere. This inconsistency in defensive coding suggests `load_event_config()` was written before the defensive pattern was established.

**No test covers:** malformed bridge entry missing `sdk_type`, or bridge entry with an unrecognized `domain_type` value.

---

### DEF-003 — Deny Hook Silently Not Installed When Method Absent
**Files:** `amplifier_module_provider_github_copilot/provider.py:256-257`, `amplifier_module_provider_github_copilot/sdk_adapter/client.py:241-243`  
**Severity:** CRITICAL — Silent sovereignty violation  

Both code paths install the deny hook conditionally:

```python
# provider.py:256-257 (test/sdk_create_fn path)
if hasattr(session, "register_pre_tool_use_hook"):
    session.register_pre_tool_use_hook(create_deny_hook())

# client.py:241-243 (real SDK path)
if hasattr(sdk_session, "register_pre_tool_use_hook"):
    sdk_session.register_pre_tool_use_hook(create_deny_hook())
    logger.debug("[CLIENT] Deny hook registered on session")
```

If the SDK session lacks `register_pre_tool_use_hook` (e.g., old SDK version, API change, mock without the method), the deny hook is **silently not installed** with no error, no warning, and no exception. The Deny+Destroy contract (`deny-destroy:DenyHook:MUST:1`) states MUST install on EVERY session — there is no "if available" clause.

**Contract violation:** `deny-destroy:DenyHook:MUST:1` — "MUST: Install a preToolUse deny hook on every SDK session" — silent degradation violates this invariant.

**Missing test:** No test verifies that a `ValueError` or `ProviderUnavailableError` is raised when `register_pre_tool_use_hook` is absent. Current tests use mock sessions that either have the method or don't raise on MagicMock attribute access.

---

## HIGH Severity

### DEF-004 — `_load_error_config_once` Missing F-036 Context Extraction
**File:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py:72-113`  
**Severity:** HIGH — Config divergence, silent feature gap  

`_load_error_config_once()` manually re-implements the YAML parsing logic from `load_error_config()` but was NOT updated when F-036 added context extraction support. It builds `ErrorMapping` objects without `context_extraction`:

```python
# client.py:88-97 — context_extraction is not parsed
mappings.append(
    ErrorMapping(
        sdk_patterns=mapping_data.get("sdk_patterns", []),
        string_patterns=mapping_data.get("string_patterns", []),
        kernel_error=mapping_data.get("kernel_error", "ProviderUnavailableError"),
        retryable=mapping_data.get("retryable", True),
        extract_retry_after=mapping_data.get("extract_retry_after", False),
        # MISSING: context_extraction=...
    )
)
```

Session-level errors (auth failures, create_session errors) flow through this function's config, not through `load_error_config()`. This means context extraction (tool_name, conflict_type, model_name, feature_name) is silently dropped for session creation failures. The `InvalidToolCallError` and `ConfigurationError` enhanced messages (F-036) will not appear in session-level error translations.

**Root cause pattern:** F-044/F-045 pattern — a feature was added in one place without updating the duplicate parsing logic in another place.

---

### DEF-005 — `extract_response_content` Infinite Recursion Risk
**File:** `amplifier_module_provider_github_copilot/provider.py:144-145`  
**Severity:** HIGH — Stack overflow on circular/self-referential objects  

```python
if hasattr(response, "data"):
    return extract_response_content(response.data)  # Unbounded recursion
```

No depth limit, no cycle detection. If `response.data` returns an object that also has `.data` (e.g., a deeply nested SDK structure, a MagicMock without spec where `.data` auto-creates a new MagicMock with `.data`), this recurses until stack overflow.

**Specific test risk:** `test_f043_sdk_response.py:test_object_with_both_data_and_content_prefers_data` uses `MagicMock()` (no spec). `mock_response.data` is set to `MockData(...)` which terminates recursion only because `MockData` happens not to have a `.data` attribute. A `MagicMock()` used as the `data` attribute would recurse infinitely.

**No test covers:** objects where `response.data.data` is not None (chained .data attributes).

---

### DEF-006 — `StreamingAccumulator.add()` Processes Events After Completion
**File:** `amplifier_module_provider_github_copilot/streaming.py:78-95`  
**Severity:** HIGH — Silent data corruption in accumulated response  

```python
def add(self, event: DomainEvent) -> None:
    if event.type == DomainEventType.CONTENT_DELTA:
        ...  # Appends to text_content
    elif event.type == DomainEventType.TURN_COMPLETE:
        self.finish_reason = event.data.get("finish_reason", "stop")
        self.is_complete = True
    elif event.type == DomainEventType.ERROR:
        self.error = event.data
        self.is_complete = True
```

After `TURN_COMPLETE` or `ERROR` sets `is_complete = True`, subsequent events continue to be processed. Events that arrive after a TURN_COMPLETE (e.g., spurious text deltas from the SDK after a tool_use stop) would corrupt the response by appending to `text_content`.

**Contract:** `streaming-contract.md` implies TURN_COMPLETE signals end of accumulation. The implementation has no guard.

**No test covers:** events arriving after TURN_COMPLETE (late text deltas after tool_use finish).

---

### DEF-007 — Broken SDK Client Not Cleaned Up After Failed `start()`
**File:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py:199-214`  
**Severity:** HIGH — Subsequent sessions use a broken client  

```python
self._owned_client = CopilotClient(options)
await self._owned_client.start()      # If this raises...
client = self._owned_client           # ...this line is never reached
```

If `start()` raises an exception, `self._owned_client` is set to the partially-initialized `CopilotClient` instance. On the next call to `session()`, `_get_client()` returns this broken client, skipping the re-initialization block. All subsequent session attempts will fail with confusing errors from the broken client rather than attempting re-initialization.

**Fix pattern:** Set `self._owned_client = None` in an exception handler around `start()`.

---

### DEF-008 — ChatRequest Multi-Turn Context Silently Dropped
**File:** `amplifier_module_provider_github_copilot/provider.py:443-458`  
**Severity:** HIGH — Data loss for multi-turn conversations  

```python
for msg in messages:
    content: Any = getattr(msg, "content", "")
    if isinstance(content, str):
        prompt_parts.append(content)
    elif isinstance(content, list):
        for block in content:
            text: str | None = getattr(block, "text", None)
            if text is not None:
                prompt_parts.append(text)
```

Only `text` blocks are extracted. `ThinkingContent`, `ToolCallContent`, tool result blocks, and non-text content blocks are **silently dropped**. In a multi-turn conversation where prior assistant messages contain tool calls and tool results, those are omitted. The prompt delivered to the SDK is missing critical context.

Additionally, all messages are joined with `"\n".join(prompt_parts)` — role information (user/assistant) is discarded. The SDK sees a single undifferentiated blob of text.

**No test covers:** multi-turn ChatRequest with mixed content types or tool call content blocks.

---

## MEDIUM Severity

### DEF-009 — `TestDenyHookNotConfigurable` Test Logic Too Weak
**File:** `tests/test_contract_deny_destroy.py:65-73`  
**Severity:** MEDIUM — Contract enforcement test does not enforce contract  

```python
assert "deny" not in key_lower or "disable" not in key_lower
```

This only catches a YAML key that contains BOTH "deny" AND "disable". Keys like `"allow_tool_execution"`, `"skip_sovereignty_check"`, `"tools_enabled"`, or `"bypass_hook"` would all pass. The test also uses `Path("config")` (relative path) — if pytest is invoked from a non-root directory, it scans zero files and passes vacuously with no assertion that files were actually scanned.

**Contract clause:** `deny-destroy:DenyHook:MUST:3` — "No configuration disables the hook." Current test cannot detect most plausible violations.

---

### DEF-010 — `_matches_mapping` Substring Match Pattern Risk
**File:** `amplifier_module_provider_github_copilot/error_translation.py:235-237`  
**Severity:** MEDIUM — Accidental broad matching  

```python
for pattern in mapping.sdk_patterns:
    if pattern in exc_type_name:  # SUBSTRING match
        return True
```

Pattern matching is substring-based, not exact. Pattern `"Error"` would match every Python exception. Pattern `"TimeoutError"` would match `"LLMTimeoutError"` (Python stdlib). If a future SDK introduces an exception class like `"SessionTimeoutError"`, it would match the existing `"TimeoutError"` pattern incorrectly.

**No test covers:** negative matching — verifying that `AuthenticationError` pattern does NOT match `NetworkAuthenticationError`.

---

### DEF-011 — `classify_event` Priority Ordering Untested
**File:** `amplifier_module_provider_github_copilot/streaming.py:231-240`  
**Severity:** MEDIUM — Ambiguous config produces silently wrong behavior  

```python
if sdk_event_type in config.bridge_mappings:
    return EventClassification.BRIDGE
if _matches_pattern(sdk_event_type, config.consume_patterns):
    return EventClassification.CONSUME
if _matches_pattern(sdk_event_type, config.drop_patterns):
    return EventClassification.DROP
```

BRIDGE takes precedence over CONSUME/DROP. If the same event type appears in both bridge mappings and consume patterns (YAML config error), BRIDGE wins silently. No test covers this ambiguous scenario. No validation in `load_event_config()` detects duplicate registrations.

---

### DEF-012 — No Test for `mount()` Exception → Returns `None`
**File:** `amplifier_module_provider_github_copilot/__init__.py:85-92`  
**Severity:** MEDIUM — Silent mount failure not detected  

`mount()` catches ALL exceptions and returns `None` for graceful degradation. No test verifies:
1. That the coordinator's `mount()` method is NOT called when provider creation fails
2. That `None` is returned (not a cleanup function) when failure occurs
3. That the error is logged (not silently swallowed at a higher level)

A bug in `GitHubCopilotProvider.__init__()` would cause mount to silently succeed (return None) with no provider registered. The kernel might not detect this.

---

### DEF-013 — `test_contract_deny_destroy.py:TestDenyHookNotConfigurable` Scans Relative Path
**File:** `tests/test_contract_deny_destroy.py:55-73`  
**Severity:** MEDIUM — Test silently passes when CWD is wrong  

```python
config_dir = Path("config")
for config_file in config_dir.glob("*.yaml"):
    ...
```

No assertion that any files were actually found. If pytest is run from any directory other than the repo root, `config_dir.glob("*.yaml")` yields nothing, and the entire test passes with zero checks performed.

**Companion:** `test_contract_errors.py:TestErrorConfigFile` uses `Path("config/errors.yaml")` with the same fragility.

---

### DEF-014 — `InvalidToolCallError` Special-Cased But Other Non-Standard Errors Not
**File:** `amplifier_module_provider_github_copilot/error_translation.py:336-350`  
**Severity:** MEDIUM — Potential `TypeError` at runtime for unknown kernel error signatures  

```python
if error_class is InvalidToolCallError:
    kernel_error = error_class(message, provider=provider, model=model, retryable=...)
else:
    kernel_error = error_class(message, provider=provider, model=model,
                               retryable=..., retry_after=retry_after)
```

Only `InvalidToolCallError` is special-cased. If any other kernel error class doesn't accept `retry_after` in its constructor (e.g., `AbortError`, `ConfigurationError`, `AccessDeniedError`), the call raises `TypeError` at runtime — which would be caught by the `except Exception` in `complete()` and re-translated, but as the WRONG error type.

This is untested because the `amplifier_core` types are imported and tested via the real library, but the constructor signatures are not verified in this codebase.

---

## LOW Severity

### DEF-015 — `MagicMock` Without `spec=` in Contract Tests
**Files:** `tests/test_contract_protocol.py:103-108`, `tests/test_contract_protocol.py:108-109`  
**Severity:** LOW — Tests may pass incorrectly  

```python
tc1 = MagicMock()   # No spec=
response = MagicMock()  # No spec=
```

`MagicMock()` without `spec=` returns a truthy Mock for ANY attribute access. The test at line 117-124 (`test_returns_empty_list_when_none`) explicitly sets `response.tool_calls = []` which is correct. But if a future test forgets to set a required attribute on an unspec'd MagicMock, `getattr(tc, "arguments", {})` returns a Mock (not `{}`), which is falsy in a different way and could produce wrong behavior.

**Best practice violation:** Golden Vision V2 and GOLDEN_VISION_FINAL both emphasize deterministic, isolated tests. `MagicMock()` without `spec=` is non-deterministic in the attributes it exposes.

---

### DEF-016 — `test_concurrent_sessions.py` Does Not Verify Deny Hook Installation
**File:** `tests/test_concurrent_sessions.py:30-31`  
**Severity:** LOW — Incomplete test coverage for concurrent deny hook installation  

```python
mock_session = MagicMock()
mock_session.disconnect = AsyncMock()
# register_pre_tool_use_hook is NOT set
```

`MagicMock()` will auto-create `register_pre_tool_use_hook` as a MagicMock callable when accessed via `hasattr()`. The `hasattr` check in `client.py:241` returns `True`, the hook is "installed" on a MagicMock callable, but the test doesn't verify that:
1. The hook was actually called on the mock
2. The hook is callable after installation
3. Five concurrent sessions each have their own deny hook installed

The race condition test only checks that `client_start_count == 1`, not that all 5 sessions have deny hooks.

---

### DEF-017 — `CopilotClientWrapper.close()` Doesn't Clear Injected Client
**File:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py:258-267`  
**Severity:** LOW — Semantic inconsistency  

`close()` sets `self._owned_client = None` but does not touch `self._sdk_client` (injected). After `close()`, `_get_client()` still returns the injected `_sdk_client`. For injected clients this is intentional (we don't own them), but it means the wrapper appears "closed" from a user perspective yet continues to use the injected client. No `_is_closed` guard prevents use after close.

---

### DEF-018 — `Path` Imported Inside Generator Function Body
**File:** `amplifier_module_provider_github_copilot/provider.py:233-234`  
**Severity:** LOW — Code consistency issue  

```python
async def complete(...):
    ...
    if error_config is None:
        from pathlib import Path   # Import inside function body
        package_root = Path(__file__).parent.parent
```

`Path` is used at module-level in `_load_models_config()` without local import, but is lazy-imported inside `complete()`. This inconsistency can cause confusion during debugging (import doesn't appear at top of file). Not a functional bug, but violates the project's own style consistency.

---

## Summary Table

| ID | Location | Severity | Category | Contract Violated |
|----|----------|----------|----------|-------------------|
| DEF-001 | `test_contract_deny_destroy.py:81`, `test_sdk_client.py:191` | CRITICAL | False Negative Test | `deny-destroy:NoExecution:MUST:3` |
| DEF-002 | `streaming.py:211-212` | CRITICAL | Startup Crash | `behaviors.md` (startup resilience) |
| DEF-003 | `provider.py:256-257`, `client.py:241-243` | CRITICAL | Silent Sovereignty Violation | `deny-destroy:DenyHook:MUST:1` |
| DEF-004 | `client.py:72-113` | HIGH | Feature Divergence (F-044/F-045 pattern) | `error-hierarchy.md` F-036 compliance |
| DEF-005 | `provider.py:144-145` | HIGH | Infinite Recursion | `sdk-response.md` |
| DEF-006 | `streaming.py:78-95` | HIGH | Post-Completion Data Corruption | `streaming-contract.md:Accumulation:MUST:1` |
| DEF-007 | `client.py:199-214` | HIGH | State Corruption After Error | `behaviors.md` (error resilience) |
| DEF-008 | `provider.py:443-458` | HIGH | Silent Data Loss | `provider-protocol.md:complete:MUST:1` |
| DEF-009 | `test_contract_deny_destroy.py:65-73` | MEDIUM | Weak Assertion | `deny-destroy:DenyHook:MUST:3` |
| DEF-010 | `error_translation.py:235-237` | MEDIUM | Latent Matching Bug | `error-hierarchy.md:Translation:MUST:2` |
| DEF-011 | `streaming.py:231-240` | MEDIUM | Silent Wrong Behavior | `event-vocabulary.md` |
| DEF-012 | `__init__.py:85-92` | MEDIUM | Missing Test Coverage | `provider-protocol.md` |
| DEF-013 | `test_contract_deny_destroy.py:55`, `test_contract_errors.py:145` | MEDIUM | Fragile Path Test | (test quality) |
| DEF-014 | `error_translation.py:336-350` | MEDIUM | Potential TypeError | `error-hierarchy.md:Translation:MUST:1` |
| DEF-015 | `test_contract_protocol.py:103-108` | LOW | MagicMock abuse (no spec=) | (test quality) |
| DEF-016 | `test_concurrent_sessions.py:30-31` | LOW | Incomplete Concurrent Test | `deny-destroy:DenyHook:MUST:1` |
| DEF-017 | `client.py:258-267` | LOW | Post-Close State | (code quality) |
| DEF-018 | `provider.py:233-234` | LOW | Style Inconsistency | (code quality) |

---

## F-044/F-045 Pattern Analysis

The F-044/F-045 bug pattern is described as code that was fixed in one place but not its duplicate. **DEF-004** is a direct instance of this pattern:

- `load_error_config()` was updated for F-036 to parse `context_extraction` fields
- `_load_error_config_once()` in `client.py` was NOT updated
- The two functions implement the same YAML parsing logic in two different places

**Architectural root cause:** `_load_error_config_once()` exists because `load_error_config()` takes a file path argument, and `_load_error_config_once()` tries importlib.resources first. The fix is to make `load_error_config()` support importlib.resources, eliminating the duplicate parsing code entirely.

---

## MagicMock Abuse Analysis

Tests using `MagicMock()` without `spec=`:

| Test File | Location | Risk Level |
|-----------|----------|------------|
| `test_contract_protocol.py` | lines 103-109, 128-134 | Low — attributes are explicitly set |
| `test_concurrent_sessions.py` | lines 30-31 | Medium — `register_pre_tool_use_hook` not verified |
| `test_f043_sdk_response.py` | lines 159-160, 169-170 | Medium — `mock_response` without spec |
| `test_f043_sdk_response.py` | line 134 | Low — `.data` attr explicitly set |

The most dangerous pattern is `MagicMock()` used for objects that are checked with `hasattr()` — since MagicMock returns `True` for ALL attribute existence checks, the conditional logic that guards the deny hook installation (`hasattr(session, "register_pre_tool_use_hook")`) always evaluates True in tests, even when the real SDK might not have this method.

---

## Highest Priority Fixes (Recommended Order)

1. **DEF-001** — Fix architecture fitness test paths immediately. Two-line fix, critical guard restored.
2. **DEF-003** — Add `raise` (or `ProviderUnavailableError`) when `register_pre_tool_use_hook` is absent.
3. **DEF-002** — Add `.get()` with defaults in `load_event_config()` bridge mapping parsing + catch `KeyError` for DomainEventType lookup.
4. **DEF-007** — Add exception handler around `await self._owned_client.start()` to clear `_owned_client` on failure.
5. **DEF-004** — Remove `_load_error_config_once()` and refactor `load_error_config()` to handle both file paths and importlib.resources.

---

*Report generated by systematic static analysis. No automated tools were run. All findings are based on code reading and cross-reference with contracts and golden vision invariants.*
