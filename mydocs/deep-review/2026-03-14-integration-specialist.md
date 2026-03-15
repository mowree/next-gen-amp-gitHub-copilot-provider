# SDK Integration Analysis — Integration Specialist Review

**Date:** 2026-03-14  
**Reviewer:** Integration Specialist (foundation:integration-specialist)  
**Scope:** SDK boundary correctness, session config, error/event handling, retry, tests, drift detection  
**Reference:** GOLDEN_VISION_V2.md, contracts/sdk-boundary.md, amplifier_module_provider_github_copilot/sdk_adapter/  

---

## Executive Summary

The implementation has made **solid progress** on the most critical invariants (deny hook, available_tools=[], mode="replace", kernel error types) but carries **three high-severity structural deviations** from the Golden Vision spec and contract. The most dangerous: the real SDK path bypasses the entire event translation pipeline, making streaming, tool capture, usage tracking, and turn completion detection non-functional in production. The architecture is correct in tests but broken for real calls.

| Dimension | Status | Severity |
|-----------|--------|----------|
| SDK types at boundary | ⚠️ Partial — structure diverges from contract | Medium |
| Session config: available_tools=[] | ✅ Correct | — |
| System message mode="replace" | ✅ Correct | — |
| Error translation completeness | ⚠️ Good but 2 mappings missing | Low |
| Event handling classification | ✅ Correct config, ⚠️ bypassed in real path | High |
| Retry logic (config-driven) | ❌ Config exists, code doesn't consume it | High |
| SDK assumption tests | ✅ Tier 6 exists, shallow session coverage | Medium |
| Breaking change detection | ⚠️ Static-only, no drift CI job | Medium |

---

## Detailed Analysis by Dimension

---

### 1. SDK Types at Boundary

**Golden Vision Requirement:**  
> Innovation 1: No SDK type crosses the membrane. Ever. A three-layer architecture (Adapter → Driver → Raw SDK) translates SDK reality into stable domain contracts.

**Contract Requirement (sdk-boundary.md):**
```
sdk_adapter/
├── __init__.py      # Exports ONLY domain types
├── _imports.py      # THE ONLY FILE with SDK imports
├── _types.py        # Domain type definitions
├── events.py        # SDK event → domain event translation
└── errors.py        # SDK error → domain error translation
```

**Actual Structure:**
```
sdk_adapter/
├── __init__.py      # Exports CopilotClientWrapper, SessionConfig, create_deny_hook
├── client.py        # Contains SDK imports (copilot.CopilotClient, copilot.types.PermissionRequestResult)
└── types.py         # SessionConfig + SDKSession = Any
```

**Gaps Found:**

1. **No `_imports.py`**: Contract MUST:2 says exactly one file `_imports.py` must hold SDK imports. This file doesn't exist. SDK imports live in `client.py` instead. This means the import quarantine relies on convention, not structure.

2. **No `sdk_adapter/events.py` or `sdk_adapter/errors.py`**: Event translation lives in root-level `streaming.py`. Error translation lives in root-level `error_translation.py`. Neither is inside `sdk_adapter/`. These modules import no SDK types directly (correct), but the contract-specified membrane directory structure is not followed.

3. **`SDKSession = Any` is not an opaque handle**: Contract requires `SessionHandle` to be a UUID string with an internal registry mapping to the real SDK session. Current implementation uses `SDKSession = Any` as a type alias, and raw SDK session objects are passed and yielded directly within `client.py`. No UUID-based handle, no registry. The handle leaks into `provider.py` as `SDKSession` type hints.

4. **`deny_permission_request` does a lazy SDK import**: Inside `client.py` (within sdk_adapter), this function does `from copilot.types import PermissionRequestResult`. Being inside `sdk_adapter/` makes this technically acceptable, but it's a conditional import in a runtime function path, not a static import in `_imports.py`. SDK version drift here would only be detected at call time, not import time.

5. **`__init__.py` exports `CopilotClientWrapper`**: The contract says `__init__.py` MUST export ONLY domain types. `CopilotClientWrapper` is an SDK-coupled wrapper, not a domain type.

**What Works Correctly:**
- Domain code outside `sdk_adapter/` does not import from `copilot.*` directly
- `SessionConfig` is a pure Python dataclass with no SDK dependencies
- `DomainEvent` in `streaming.py` uses primitive types only

---

### 2. Session Configuration — available_tools=[]

**Contract:** `sdk-boundary:Config:MUST:1` — MUST set `available_tools: []`

**Implementation (client.py lines 216-220):**
```python
session_config: dict[str, Any] = {}
# F-045: Disable ALL SDK/CLI built-in tools.
session_config["available_tools"] = []
```

**Status: ✅ COMPLIANT**

`available_tools=[]` is set unconditionally on every session, before any conditional logic. The rationale is documented in both the code and the contract. Tests in `test_sdk_boundary_contract.py` verify this with `ConfigCapturingMock`.

---

### 3. System Message Mode

**Contract:** `sdk-boundary:Config:MUST:2` — MUST use `system_message.mode: "replace"` when provided

**Implementation (client.py lines 223-227):**
```python
if system_message:
    # F-044: Use replace mode to ensure Amplifier bundle persona takes precedence.
    session_config["system_message"] = {"mode": "replace", "content": system_message}
```

**Status: ✅ COMPLIANT**

Mode is hardcoded to `"replace"` — correctly treated as mechanism, not policy (non-configurable per Golden Vision). Tests in `test_sdk_boundary_contract.py` verify both the mode and absence of system_message key when not provided.

---

### 4. Error Translation Completeness

**Golden Vision Requirement (v2.1 correction):**  
Must use kernel types from `amplifier_core.llm_errors.*`, not custom hierarchy.

**Implementation:**
- `error_translation.py` imports all kernel types from `amplifier_core.llm_errors` ✅
- `KERNEL_ERROR_MAP` maps string names to classes ✅
- Config-driven via `config/errors.yaml` ✅
- `translate_sdk_error()` always returns (never raises) ✅
- Original exception preserved via `__cause__` ✅
- F-036 context extraction implemented ✅

**Mapping completeness comparison (Golden Vision spec vs. actual):**

| Golden Vision Mapping | In errors.yaml | Notes |
|----------------------|---------------|-------|
| AuthenticationError | ✅ `AuthenticationError`, retryable=false | |
| RateLimitError | ✅ `RateLimitError`, retryable=true, extract_retry_after | |
| LLMTimeoutError | ✅ `LLMTimeoutError`, retryable=true | |
| ContentFilterError | ✅ `ContentFilterError`, retryable=false | |
| NotFoundError | ✅ `NotFoundError`, retryable=false | |
| ProviderUnavailableError | ✅ CircuitBreakerError → `ProviderUnavailableError` | |
| NetworkError | ✅ `NetworkError`, retryable=true | |
| AbortError | ❌ No mapping — falls to default `ProviderUnavailableError` | Missing |
| SessionCreateError/DestroyError | ❌ No mapping — falls to default | Golden Vision listed these |
| QuotaExceededError | ✅ Added as separate mapping (beyond Golden Vision) | Good addition |
| ContextLengthError | ✅ Added (beyond Golden Vision) | Good addition |
| StreamError | ✅ Added (beyond Golden Vision) | Good addition |
| InvalidToolCallError | ✅ Added (beyond Golden Vision) | Good addition |
| ConfigurationError | ✅ Added (beyond Golden Vision) | Good addition |

**Default behavior:** Falls through to `ProviderUnavailableError` with `retryable=True`. This is correct per the contract.

**Gaps:**
- `AbortError` has no mapping. An SDK-level abort would be translated to `ProviderUnavailableError(retryable=True)`, which could cause spurious retry on user-initiated cancellation.
- Session lifecycle errors (`SessionCreateError`, `SessionDestroyError`) are not explicitly mapped. They would fall to the default.

**Status: ⚠️ MOSTLY COMPLIANT — 2 missing mappings with behavioral impact**

---

### 5. Event Handling Classification

**Golden Vision Requirement:**  
~58 SDK event types → 6 stable domain types, driven by `config/events.yaml`. BRIDGE/CONSUME/DROP classification.

**Config correctness (`config/events.yaml`):**

| Domain Event | SDK Source | In Config | Classification |
|-------------|-----------|-----------|----------------|
| CONTENT_DELTA (TEXT) | text_delta | ✅ | BRIDGE |
| CONTENT_DELTA (THINKING) | thinking_delta | ✅ | BRIDGE |
| TOOL_CALL | tool_use_complete | ✅ | BRIDGE |
| TURN_COMPLETE | message_complete | ✅ | BRIDGE |
| USAGE_UPDATE | usage_update | ✅ | BRIDGE |
| SESSION_IDLE | session_idle | ✅ | BRIDGE |
| ERROR | error | ✅ | BRIDGE |
| tool_use_start, tool_use_delta | — | ✅ | CONSUME |
| session_created, session_destroyed | — | ✅ | CONSUME |
| usage | — | ✅ | CONSUME |
| system_notification | — | ✅ | CONSUME (SDK v0.1.33 addition) |
| tool_result_*, mcp_*, permission_*, etc. | — | ✅ | DROP (wildcard patterns) |

The `finish_reason_map` translates SDK reasons (`end_turn` → `STOP`, etc.) correctly.

Unknown events default to DROP with a `logger.warning` — correct behavior.

**Critical Gap — Real SDK Path Bypasses Event Pipeline:**

In `provider.py` lines 479-498 (the real SDK execution path):

```python
# Real SDK path: use client wrapper
model = internal_request.model or "gpt-4o"
async with self._client.session(model=model) as sdk_session:
    # SDK uses send_and_wait() for blocking call
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
    
    # Extract response content and convert to domain event
    if sdk_response is not None:
        content = extract_response_content(sdk_response)
        text_event = DomainEvent(
            type=DomainEventType.CONTENT_DELTA,
            data={"text": content},
        )
        accumulator.add(text_event)
```

**This is a structural correctness failure.** The real production path:
1. Uses `send_and_wait()` instead of streaming iteration
2. Generates ONE synthetic `CONTENT_DELTA` event and nothing else
3. Never generates `TOOL_CALL` events → tool use is broken in production
4. Never generates `USAGE_UPDATE` events → usage tracking is broken
5. Never generates `TURN_COMPLETE` events → finish_reason is always absent
6. Never uses `translate_event()` or `config/events.yaml` at all

The test path (via `sdk_create_fn`) correctly uses the streaming pipeline. The real path does not. This means the event classification config is correct but never exercised in production.

**Status: ❌ CONFIG CORRECT, REAL PATH BYPASSES IT**

---

### 6. Retry Logic — Config-Driven

**Golden Vision Requirement:**  
`config/retry.yaml` defines retry policy. Python reads this config. Hardcoded `MAX_RETRIES = 3` is an explicit anti-pattern.

**Config file (`config/retry.yaml`):**  
```yaml
retry:
  max_attempts: 3
  backoff:
    strategy: exponential_with_jitter
    base_delay_ms: 1000
    max_delay_ms: 30000
    jitter_factor: 0.1
circuit_breaker:
  soft_turn_limit: 3
  hard_turn_limit: 10
  timeout_buffer_seconds: 5.0
```

The config file exists and is correctly structured.

**Implementation gap:** No Python code reads `config/retry.yaml`. Searching across:
- `provider.py` — no retry logic, no import of retry config
- `error_translation.py` — translates errors but no retry
- `streaming.py` — no retry
- `sdk_adapter/client.py` — no retry loop

There is **zero retry implementation**. The `retry.yaml` config is pure documentation at this point. When a retryable error occurs (e.g., `RateLimitError`), it is translated to a kernel error type with `retryable=True`, but the provider itself makes no retry attempt. The kernel/orchestrator would need to implement retry — which is outside the provider's scope per the Vision, but the provider is supposed to implement internal retry for transient SDK failures.

**The circuit breaker is also absent.** No code enforces `soft_turn_limit` or `hard_turn_limit` from the config.

**Status: ❌ CONFIG EXISTS, CODE DOES NOT CONSUME IT**

---

### 7. SDK Assumption Tests

**Golden Vision Requirement (Tier 6):**  
SDK assumption tests with recorded responses, shape validation, drift detection.

**Existing tests (`tests/test_sdk_assumptions.py`):**

| Test Class | What It Tests | Depth |
|-----------|--------------|-------|
| `TestSDKImportAssumptions` | `copilot` module importable, `CopilotClient` exists, `create_session` method, `start`/`stop` lifecycle, `CopilotClient({github_token: ...})` | Shape only |
| `TestSessionInterfaceAssumptions` | `create_session` method exists, `on_permission_request` requirement documented | Shallow |
| `TestOurWrapperImports` | `CopilotClientWrapper` importable, `create_deny_hook` works, session method exists | Import verification |
| `TestHelperFunctions` | `get_event_type`, `get_event_field`, `describe_event`, `collect_event_types` etc. | Our helpers only |

**Gaps:**

1. **Session object interface not tested at Tier 6**: The contract notes that `disconnect()`, `send_and_wait()` (or `send_message()`), and `register_pre_tool_use_hook()` are deferred to Tier 7 (live tests). This means a breaking SDK rename of `send_and_wait` would not be detected without credentials.

2. **`send_and_wait()` assumption not documented**: The real SDK path uses `send_and_wait()` but this method name is not in any Tier 6 assumption test. If SDK renames it to `send_message()` or `query()`, the test suite passes but production breaks.

3. **No recorded response shape validation**: Tier 6 per Golden Vision should include "recorded responses, shape validation." No fixture responses are used; tests only verify class structure.

4. **`PermissionRequestResult` shape not tested**: The `deny_permission_request()` function constructs `PermissionRequestResult(kind=..., message=...)` but no assumption test verifies this type exists with these fields.

**What works well:**
- Tests are properly marked `@pytest.mark.sdk_assumption`
- They reference contract clauses
- `TestOurWrapperImports` verifies the deny hook factory works correctly

**Status: ⚠️ TIER 6 EXISTS BUT SHALLOW — Session interface and response shapes not covered**

---

### 8. Breaking Change Detection

**Golden Vision Requirement:**  
Weekly SDK change detection CI job that checks config mappings against SDK reality, creates GitHub Issue on drift.

**Current mechanisms:**

| Mechanism | Present | Coverage |
|-----------|---------|----------|
| Tier 6 SDK assumption tests (static structure) | ✅ | CopilotClient class shape |
| Tier 7 live tests (`test_live_sdk.py`) | ✅ | Session interface (requires credentials) |
| Weekly CI drift detection job | ❌ | Not implemented |
| Auto-create config update PR on API shape change | ❌ | Not implemented |
| Architecture fitness test (no SDK imports outside sdk_adapter/) | ❌ | Not implemented |
| `_imports.py` as single import point (enables grep-based auditing) | ❌ | Structure not followed |

The primary protection is the Tier 7 live test suite, which is credential-gated and not suitable for CI on every commit. The static Tier 6 tests would catch top-level class renames but not method signature changes, field renames, or behavioral changes.

**How a breaking change would manifest today:**
- SDK renames `send_and_wait` → `query`: Production silently breaks with `AttributeError`. No test catches it without credentials.
- SDK changes `SessionConfig.available_tools` field name: `ConfigCapturingMock` tests catch it at the wrapper level, but real SDK sessions would fail silently.
- SDK adds required new field to session config: Would fail at session creation time with a runtime error, not a test-time signal.

**Status: ❌ NO AUTOMATED DRIFT DETECTION — Relies on manual live testing**

---

## Findings Summary Table

| Finding | Severity | Category |
|---------|----------|---------|
| Real SDK path uses `send_and_wait()` — bypasses streaming, event translation, tool capture | **Critical** | Correctness |
| `provider.close()` is a no-op — `CopilotClientWrapper` never closed | **High** | Resource leak |
| No retry implementation despite `config/retry.yaml` existing | **High** | Behavior |
| No circuit breaker implementation | **High** | Behavior |
| `_imports.py` missing — SDK imports in `client.py` not isolated | **Medium** | Structure |
| `events.py` and `errors.py` missing from `sdk_adapter/` | **Medium** | Structure |
| `SessionHandle` as UUID + registry not implemented | **Medium** | Structure |
| `__init__.py` exports `CopilotClientWrapper` (SDK-coupled, not domain type) | **Medium** | Contract |
| `AbortError` not mapped — user aborts become retryable `ProviderUnavailableError` | **Medium** | Correctness |
| `SessionCreateError`/`SessionDestroyError` not mapped | **Low** | Completeness |
| Tier 6 tests don't verify session method interface (`send_and_wait`, `disconnect`) | **Medium** | Test coverage |
| No automated SDK drift detection CI job | **Medium** | Maintainability |

---

## Conformance by Golden Vision Principle

| Principle | Conformance | Notes |
|-----------|------------|-------|
| P1: Translation, Not Framework | ⚠️ Partial | Real path does non-streaming translation incorrectly |
| P2: Three Mediums (Python/YAML/Markdown) | ⚠️ Partial | YAML configs exist but retry/circuit-breaker not consumed |
| P3: Mechanism with Sensible Defaults | ⚠️ Partial | Deny+Destroy is non-configurable ✅; retry defaults in YAML but no mechanism |
| P4: Design for SDK Evolution | ⚠️ Partial | Config-driven errors ✅; session interface not evolution-proof |
| P5: AI-Maintainability | ✅ Good | Module sizes within limits; contracts referenced in code |
| P6: Confidence-Gated Autonomy | ✅ Good | Architecture supports it; not yet exercised |
| Non-Negotiable: No SDK type crosses boundary | ⚠️ Mostly | Structure deviates; real leakage minimal |
| Non-Negotiable: preToolUse deny hook on every session | ✅ Compliant | Verified by contract tests |
| Non-Negotiable: Sessions are ephemeral | ✅ Compliant | `asynccontextmanager` enforces destroy |
| Non-Negotiable: Deny+Destroy never configurable | ✅ Compliant | Hardcoded, no YAML knob |

---

## Recommended Actions

### Immediate (Correctness Blockers)

1. **Fix real SDK path to use streaming**: Replace `send_and_wait()` with streaming iteration over SDK events, routing through `translate_event()`. The test path (`sdk_create_fn`) already shows the correct pattern.

2. **Fix `provider.close()` to call `self._client.close()`**: Current no-op leaks the `CopilotClientWrapper` and its owned client.

3. **Map `AbortError` in `config/errors.yaml`**: Add mapping for user abort patterns so they produce `AbortError(retryable=False)` instead of `ProviderUnavailableError(retryable=True)`.

### Near-Term (Architecture Debt)

4. **Implement retry from `config/retry.yaml`**: Either in the provider's `complete()` method for transient errors, or document explicitly that retry is delegated entirely to the kernel. Don't leave the config as dead data.

5. **Create `sdk_adapter/_imports.py`**: Move all `from copilot import ...` statements to a single `_imports.py` file, enabling grep-based auditing and structure-enforced quarantine.

6. **Add Tier 6 assumption test for `send_and_wait()`**: `assert hasattr(session_class, "send_and_wait")` — currently impossible without live session creation; document this as a known gap in `test_sdk_assumptions.py`.

### Maintenance (Config-First Vision Completion)

7. **Circuit breaker implementation**: Add turn counting and enforce `soft_turn_limit`/`hard_turn_limit` from `config/retry.yaml`.

8. **SDK drift detection**: Add a weekly CI job that runs Tier 6 assumption tests and creates a GitHub Issue if SDK version has changed since last known-good.

---

## Reference: Contract Clauses vs. Implementation

| Contract Clause | Clause Text | Status |
|----------------|-------------|--------|
| `sdk-boundary:Membrane:MUST:1` | All SDK imports in adapter only | ✅ |
| `sdk-boundary:Membrane:MUST:2` | Only `_imports.py` has SDK imports | ❌ |
| `sdk-boundary:Types:MUST:1` | No SDK types cross boundary | ✅ (mostly) |
| `sdk-boundary:Types:MUST:3` | SessionHandle is opaque string | ❌ |
| `sdk-boundary:Config:MUST:1` | available_tools is empty list | ✅ |
| `sdk-boundary:Config:MUST:2` | system_message mode is replace | ✅ |
| `sdk-boundary:Config:MUST:3` | on_permission_request always set | ✅ |
| `sdk-boundary:Config:MUST:4` | streaming is true | ✅ |
| `sdk-boundary:Config:MUST:5` | deny hook registered post-creation | ✅ |
| `sdk-boundary:Config:MUST:6` | no unknown keys in config | ✅ (verified by test) |
| Golden Vision Non-Negotiable 2 | preToolUse deny hook, no exceptions | ✅ |
| Golden Vision Non-Negotiable 3 | Sessions ephemeral, destroy after use | ✅ |
| Golden Vision Non-Negotiable 6 | Deny+Destroy never configurable | ✅ |
| Golden Vision Principle 2 | YAML config drives retry/events/errors | ⚠️ Events/errors ✅, retry ❌ |

---

*Analysis performed by foundation:integration-specialist, 2026-03-14*

---

## VERIFICATION — 2026-03-14 (Post-Review Accuracy Check)

**Verification scope:** Each "production-breaking" or high-severity claim re-checked against actual source files.

---

### Issue #1: Real SDK path bypasses event pipeline

**Verdict: CONFIRMED. Genuinely production-breaking.**

Code verified at `provider.py:479–495` (class `GitHubCopilotProvider.complete()`):

```python
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
    if sdk_response is not None:
        content = extract_response_content(sdk_response)
        text_event = DomainEvent(type=DomainEventType.CONTENT_DELTA, data={"text": content})
        accumulator.add(text_event)
```

Exactly as described: `send_and_wait()`, one synthetic `CONTENT_DELTA`, no call to `translate_event()`, no tool call events, no usage events, no `TURN_COMPLETE`. This is a real production path and it is structurally broken for tool use and usage tracking.

**One correction:** The document analysed the *module-level* `complete()` function as if it had both a test path and a real SDK path. This is **outdated**. The current module-level `complete()` (lines 258–264) raises `ProviderUnavailableError` unconditionally when `sdk_create_fn` is `None`:

```python
else:
    raise ProviderUnavailableError(
        "Real SDK path requires CopilotClientWrapper.session() context manager.",
        ...
    )
```

The real SDK path lives *only* inside `GitHubCopilotProvider.complete()`. The description of the bug is still correct; only the location attribution was imprecise.

---

### Issue #2: `provider.close()` is a no-op / `CopilotClientWrapper` never closed

**Verdict: CONFIRMED as described, but partially mis-framed. Real resource leak, NOT immediately production-breaking.**

`provider.close()` at lines 517–523 is:

```python
async def close(self) -> None:
    # Currently no resources to clean up
    pass
```

This is confirmed. The provider holds `self._client = CopilotClientWrapper()` which, after lazy init, owns a live `CopilotClient` that has been `.start()`ed. `provider.close()` never calls `self._client.close()`.

**Correction to framing:** The document implies `CopilotClientWrapper` has no close mechanism. This is wrong. `CopilotClientWrapper.close()` is fully implemented at `client.py:258–267` and correctly calls `self._owned_client.stop()`. The bug is that `provider.close()` never invokes it.

**Production-breaking assessment:** This is a resource leak on shutdown, not a functional failure during operation. The provider works correctly while running; the SDK client is simply not stopped when the provider is closed. Severity is **High (resource leak)**, not **Critical (won't work)**.

---

### Issue #3: No retry implementation despite `config/retry.yaml`

**Verdict: CONFIRMED. Missing feature, NOT production-breaking.**

There is zero retry logic in `provider.py`, `streaming.py`, or `sdk_adapter/client.py`. The `config/retry.yaml` file is dead configuration. When a retryable error (e.g., `RateLimitError`) occurs, it is correctly translated with `retryable=True` and propagated — but no retry loop exists at the provider level.

**Production-breaking assessment:** This is a missing feature. The provider does not silently break — it correctly raises a translated error with the right `retryable` flag so that upstream callers (kernel/orchestrator) can decide to retry. Severity is **High (incomplete spec conformance)**, not **production-breaking in the "won't work" sense**.

---

### Issue #4: `provider.close()` no-op also omits circuit breaker

**Verdict: CONFIRMED. Same category as retry — missing feature, not broken behavior.**

---

### SDK Boundary Claims — Re-verification

| Claim | Verified | Notes |
|-------|----------|-------|
| No `_imports.py` file | ✅ CONFIRMED | `sdk_adapter/` has only `__init__.py`, `client.py`, `types.py` |
| No `events.py` or `errors.py` in `sdk_adapter/` | ✅ CONFIRMED | Both live at package root level |
| `SDKSession = Any` (not UUID handle) | ✅ CONFIRMED | `types.py:32`: `SDKSession = Any` |
| `deny_permission_request` lazy SDK import | ✅ CONFIRMED | `client.py:57`: conditional `from copilot.types import PermissionRequestResult` |
| `__init__.py` exports `CopilotClientWrapper` | ✅ CONFIRMED | `__init__.py:17–20` |
| `available_tools=[]` set unconditionally | ✅ CONFIRMED | `client.py:220` |
| `system_message mode="replace"` | ✅ CONFIRMED | `client.py:227` |
| `streaming=True` always set | ✅ CONFIRMED | `client.py:229` (not noted in original doc) |

---

### Corrected Severity Classification

| Finding | Claimed Severity | Verified Severity | Actually Production-Breaking? |
|---------|-----------------|-------------------|-------------------------------|
| Real SDK path uses `send_and_wait()` — no streaming, no tool events | Critical | **Critical** | **YES** — tool use non-functional |
| `provider.close()` is a no-op — client never stopped | High | High | No — resource leak, not functional failure |
| No retry despite `config/retry.yaml` | High | High | No — missing feature, errors propagate correctly |
| No circuit breaker | High | High | No — missing feature |
| `_imports.py` missing | Medium | Medium | No — structural debt |
| `events.py`/`errors.py` outside `sdk_adapter/` | Medium | Medium | No — structural debt |
| `SessionHandle` as UUID not implemented | Medium | Medium | No — structural debt |
| `AbortError` not mapped | Medium | Medium | Marginal — causes spurious retry on user abort |

**Summary:** Of the claimed "3 production-breaking issues," **1 is genuinely production-breaking** (Issue #1: real SDK path bypasses event pipeline). Issues #2 and #3 are real bugs/gaps but do not cause the provider to stop working — they are resource leaks and missing features respectively.

*Verification performed 2026-03-14 against actual source files.*

---

## PRINCIPAL REVIEW AND AMENDMENTS

**Reviewed by:** Principal-Level Developer  
**Date:** 2026-03-15  
**Document Rating:** 9/10 — Best in the review set

### Verified Correct ✅

The following findings are confirmed accurate and demonstrate excellent integration analysis:

1. **Real SDK path uses `send_and_wait()`, bypasses event pipeline** — CONFIRMED P0 at provider.py:479-495
2. **`provider.close()` is no-op, never calls `_client.close()`** — CONFIRMED at lines 517-523
3. **client.py HAS working `close()` implementation** — CONFIRMED at lines 258-268
4. **retry.yaml exists but no code consumes it** — CONFIRMED, F-075 spec exists
5. **Self-verification section** — Excellent intellectual honesty in re-checking claims

### Critical Addition: Missing Error Translation Gap 🚨

**Original Document:** Catches that real path bypasses EVENT translation ✓  
**Amendment:** Real SDK path ALSO bypasses ERROR translation

**Evidence:**
```python
# provider.py:481-483 — NO try/except
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```

If `send_and_wait()` throws, the exception propagates **untranslated** to the kernel. This is P0.

**Remediation:** F-072 spec covers this fix.

### New Bug Identified: provider.close() No-Op (P1)

The document correctly identified that `provider.close()` is a no-op while `client.close()` exists and works. This is a resource leak / cleanup issue.

**Remediation:** F-082 spec created — Wire provider.close() to call client.close()

### Summary of Specs from This Review

- **F-072** (P0): Real SDK path error/event translation (referenced, already exists)
- **F-075** (P1): Wire retry.yaml (referenced, already exists)
- **F-082** (P1): Wire provider.close() to client.close() (NEW)

---

*End of principal amendments. Original findings retained — excellent integration analysis.*
