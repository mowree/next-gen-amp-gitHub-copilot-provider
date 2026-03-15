# Deep Review: Test Coverage Analysis
**Date:** 2026-03-14  
**Scope:** Full test suite vs. all contracts  
**Method:** Manual read of all 38 test files, 5 source modules, 8 contracts, and F-047 spec

---

## Executive Summary

The test suite has been significantly strengthened by F-046/F-047 work. The critical F-044/F-045 bugs that survived 42 features now have boundary contract tests. However, **three major coverage gaps remain**:

1. **`contracts/behaviors.md` is entirely untested** — retry policy, circuit breaker, streaming timing, and model alias behaviors have zero test coverage despite having defined MUST clauses.
2. **Ephemeral session invariants are only structure-tested** — the deny-destroy:Ephemeral family (new session per call, no reuse) is untested at the behavioral level.
3. **`TestArchitectureFitness` tests a nonexistent path** — the SDK import quarantine test uses `src/amplifier_module_provider_github_copilot` but the actual module is at `amplifier_module_provider_github_copilot/`. It passes vacuously.

---

## PRINCIPAL REVIEW AND AMENDMENTS

**Document rating:** 8/10 — comprehensive review with distinctive value, including independent discovery of DEF-001 (`TestArchitectureFitness` scanning the wrong path) and a useful analysis of `MagicMock` forgiveness risks.

### Retracted finding

- **RETRACTED:** the prior claim that `StreamingAccumulator.to_chat_response()` lacked dedicated tests was incorrect.
- Verified coverage exists in `tests/test_f038_kernel_integration.py`:
  - `test_to_chat_response_returns_kernel_type`
  - `test_to_chat_response_uses_text_block`
  - `test_to_chat_response_uses_thinking_block`
- The coverage matrix should therefore treat `streaming:Response:MUST:1` as **✅ covered**, and the broader claim that the F-038 kernel conversion path had no dedicated tests is withdrawn.

### Findings retained as valid

- **KEEP:** **DEF-001** — `TestArchitectureFitness` scans `src/amplifier_module_provider_github_copilot`, but the real package is `amplifier_module_provider_github_copilot/`, so the quarantine test passes vacuously.
- **KEEP:** **`contracts/behaviors.md` has zero behavioral coverage** — existing tests touch error patterns and config structure, not retry/circuit-breaker behavior.
- **KEEP:** **Ephemeral session invariants are structure-tested only** — there is still no behavioral test proving that two `complete()` calls create distinct sessions with no reuse.
- **KEEP:** `test_contract_events.py:98` constructs `DomainEvent(type="CONTENT_DELTA", ...)` with a `str` instead of `DomainEventType`.
- **KEEP:** `_imports.py` is still missing even though the current SDK-boundary contract expects a single quarantine import file.

### Missed observation added after principal review

- **ADD:** the dominant P0 issue is not just that the real SDK path is under-tested; it is also **architecturally missing error translation entirely**.
- In `amplifier_module_provider_github_copilot/provider.py` (real SDK path at lines 479-495 in this review), `sdk_session.send_and_wait(...)` is executed without a local `try/except` and without a call to `translate_sdk_error(...)`.
- That means raw SDK exceptions can escape the provider boundary even if live-path tests are later added. This is a **code bug**, already aligned with **F-072**.

### New specs from principal review

- **F-090 (P1):** Add behavioral tests for `contracts/behaviors.md` coverage, especially retry policy and circuit breaker behavior.
- **F-091 (P1):** Add ephemeral session invariant tests that prove two sessions are distinct and not reused.

---

## Coverage Matrix: Module vs. Contract Clauses

| Contract Anchor | Clause | Test File | Status |
|---|---|---|---|
| **provider-protocol:name:MUST:1** | Returns "github-copilot" | test_contract_protocol.py | ✅ |
| **provider-protocol:name:MUST:2** | Is a property | test_contract_protocol.py | ✅ |
| **provider-protocol:get_info:MUST:1** | Returns valid ProviderInfo | test_contract_protocol.py | ✅ |
| **provider-protocol:get_info:MUST:2** | Includes context_window | test_contract_protocol.py | ⚠️ checks capabilities, not context_window |
| **provider-protocol:list_models:MUST:1** | Returns model list | test_contract_protocol.py | ✅ |
| **provider-protocol:list_models:MUST:2** | Includes context_window | test_contract_protocol.py | ✅ |
| **provider-protocol:complete:MUST:1** | Creates ephemeral session | test_contract_protocol.py | ⚠️ only checks **kwargs signature |
| **provider-protocol:complete:MUST:2** | Captures tool calls | (various) | ⚠️ indirect via streaming tests |
| **provider-protocol:complete:MUST:3** | Destroys session after turn | test_sdk_boundary_contract.py | ⚠️ disconnect called via fixture |
| **provider-protocol:complete:MUST:4** | No state between calls | — | ❌ missing |
| **provider-protocol:parse_tool_calls:MUST:1** | Extracts tool calls | test_contract_protocol.py | ✅ |
| **provider-protocol:parse_tool_calls:MUST:2** | Returns empty list when none | test_contract_protocol.py | ✅ |
| **provider-protocol:parse_tool_calls:MUST:3** | Preserves tool call IDs | test_contract_protocol.py | ✅ |
| **provider-protocol:parse_tool_calls:MUST:4** | Uses arguments, not input | test_contract_protocol.py | ✅ |
| **deny-destroy:DenyHook:MUST:1** | preToolUse hook installed on every session | test_sdk_boundary_contract.py, test_contract_deny_destroy.py | ✅ |
| **deny-destroy:DenyHook:MUST:2** | Hook returns DENY for all tool requests | test_contract_deny_destroy.py | ✅ |
| **deny-destroy:DenyHook:MUST:3** | No configuration disables the hook | test_contract_deny_destroy.py | ✅ |
| **deny-destroy:Ephemeral:MUST:1** | New session per complete() call | — | ❌ missing |
| **deny-destroy:Ephemeral:MUST:2** | Session destroyed after first turn | — | ❌ missing |
| **deny-destroy:Ephemeral:MUST:3** | No session reuse | — | ❌ missing |
| **deny-destroy:NoExecution:MUST:1** | Tool requests captured from events | test_streaming.py | ⚠️ accumulator tested, not via complete() |
| **deny-destroy:NoExecution:MUST:2** | Tool requests returned to orchestrator | — | ❌ missing |
| **deny-destroy:NoExecution:MUST:3** | SDK never executes tools | test_contract_deny_destroy.py | ⚠️ BROKEN — tests nonexistent path |
| **deny-destroy:ToolSuppression:MUST:1** | available_tools=[] on every session | test_sdk_boundary_contract.py | ✅ |
| **deny-destroy:ToolSuppression:MUST:2** | SDK built-in tools never visible to LLM | — | ❌ missing (live test only) |
| **error-hierarchy:Kernel:MUST:1** | Uses kernel types only | test_contract_errors.py, test_error_translation.py | ✅ |
| **error-hierarchy:Kernel:MUST:2** | Sets provider attribute | test_error_translation.py, test_contract_errors.py | ✅ |
| **error-hierarchy:Translation:MUST:1** | Never raises | test_error_translation.py, test_contract_errors.py | ✅ |
| **error-hierarchy:Translation:MUST:2** | Uses config patterns | test_error_translation.py | ✅ |
| **error-hierarchy:Translation:MUST:3** | Chains original exception | test_error_translation.py | ✅ |
| **error-hierarchy:RateLimit:MUST:1** | Extracts retry_after | test_error_translation.py | ✅ |
| **error-hierarchy:Default:MUST:1** | Falls through to ProviderUnavailableError | test_error_translation.py, test_contract_errors.py | ✅ |
| **event-vocabulary:Events:MUST:1** | 6 domain events defined | test_streaming.py, test_contract_events.py | ✅ |
| **event-vocabulary:Bridge:MUST:1** | BRIDGE events translated | test_streaming.py | ✅ |
| **event-vocabulary:Bridge:MUST:2** | Uses config classification | test_streaming.py | ✅ |
| **event-vocabulary:Consume:MUST:1** | CONSUME events processed internally | test_streaming.py | ✅ |
| **event-vocabulary:Drop:MUST:1** | DROP events ignored | test_streaming.py | ✅ |
| **event-vocabulary:FinishReason:MUST:1** | SDK reasons mapped correctly | test_contract_events.py | ✅ |
| **streaming:ContentTypes:MUST:1** | Uses kernel content types | test_f038_kernel_integration.py | ✅ |
| **streaming:Accumulation:MUST:1** | Deltas accumulated in order | test_contract_streaming.py, test_streaming.py | ✅ |
| **streaming:Accumulation:MUST:2** | Block boundaries maintained | test_contract_streaming.py, test_streaming.py | ✅ |
| **streaming:ToolCapture:MUST:1** | Tool calls captured | test_contract_streaming.py, test_streaming.py | ✅ |
| **streaming:ToolCapture:MUST:2** | Tool calls in final response | test_contract_streaming.py | ✅ |
| **streaming:CircuitBreaker:MUST:1** | Respects hard limit | — | ❌ missing |
| **streaming:Response:MUST:1** | Final response uses kernel types | test_f038_kernel_integration.py | ✅ |
| **sdk-boundary:Membrane:MUST:1** | All SDK imports in adapter only | test_contract_deny_destroy.py | ⚠️ BROKEN — scans nonexistent src/ path |
| **sdk-boundary:Membrane:MUST:2** | Only _imports.py has SDK imports | — | ❌ _imports.py doesn't exist; client.py has SDK imports directly |
| **sdk-boundary:Types:MUST:1** | No SDK types cross boundary | — | ❌ missing |
| **sdk-boundary:Types:MUST:2** | Domain types are dataclasses/primitives | — | ❌ missing |
| **sdk-boundary:Types:MUST:3** | SessionHandle is opaque string | — | ❌ missing |
| **sdk-boundary:Translation:MUST:1** | Events translated to DomainEvent | test_streaming.py | ✅ |
| **sdk-boundary:Translation:MUST:2** | Errors translated to domain exceptions | test_error_translation.py | ✅ |
| **sdk-boundary:Membrane:MUST:5** | Fail at import time if SDK not installed | test_sdk_boundary.py | ✅ |
| **sdk-boundary:Config:MUST:1** | available_tools is empty list | test_sdk_boundary_contract.py | ✅ |
| **sdk-boundary:Config:MUST:2** | system_message mode is replace | test_sdk_boundary_contract.py | ✅ |
| **sdk-boundary:Config:MUST:3** | on_permission_request always set | test_sdk_boundary_contract.py | ✅ |
| **sdk-boundary:Config:MUST:4** | streaming is true | test_sdk_boundary_contract.py | ✅ |
| **sdk-boundary:Config:MUST:5** | deny hook registered post-creation | test_sdk_boundary_contract.py | ✅ |
| **sdk-boundary:Config:MUST:6** | no unknown keys in config | test_sdk_boundary_contract.py | ✅ |
| **behaviors:Retry:MUST:1** | Respects max_attempts | — | ❌ missing |
| **behaviors:Retry:MUST:2** | Applies backoff | — | ❌ missing |
| **behaviors:Retry:MUST:3** | Only retries retryable errors | — | ❌ missing |
| **behaviors:Retry:MUST:4** | Honors retry_after | — | ❌ missing |
| **behaviors:CircuitBreaker:MUST:1** | Tracks turn count | — | ❌ missing |
| **behaviors:CircuitBreaker:MUST:2** | Errors at hard limit | — | ❌ missing |
| **behaviors:Streaming:MUST:1** | Warns on slow TTFT | — | ❌ missing |
| **behaviors:Models:MUST:1** | Resolves aliases | — | ❌ missing |
| **behaviors:Models:MUST:2** | Raises NotFoundError for invalid | — | ❌ missing |

**Summary:**
- ✅ Fully covered: 37 clauses
- ⚠️ Partially covered / broken: 8 clauses
- ❌ Not covered: 19 clauses

---

## Section 1: Contract Anchor Coverage — Detailed Findings

### 1.1 Provider Protocol (`contracts/provider-protocol.md`)

**Strong coverage** for the `name`, `list_models`, and `parse_tool_calls` methods.

**Gap — `get_info:MUST:2`**: The contract says "MUST include `defaults.context_window` for budget calculation." The test `test_includes_capabilities` checks for `"streaming"` and `"tool_use"` in capabilities. The contract anchor is for `context_window` in defaults — this is a wrong assertion. The test would pass even if `context_window` was missing from defaults.

**Gap — `complete:MUST:1,2,3,4`**: `test_accepts_kwargs` is the only `complete()` test. It uses `inspect.signature` to check for `**kwargs` — this is an interface test, not a behavioral test. There are no tests that:
- Call `complete()` twice and verify two distinct sessions are created (MUST:1, MUST:4)
- Verify a tool call in the response came from event capture, not SDK execution (MUST:2)
- Verify the session's `disconnect()` was called after `complete()` returns (MUST:3)

### 1.2 Deny + Destroy (`contracts/deny-destroy.md`)

**Strong coverage** for the hook itself (MUST:1,2,3) and tool suppression (ToolSuppression).

**Critical Bug — `TestArchitectureFitness::test_no_sdk_imports_outside_adapter`:**
```python
root = Path("src/amplifier_module_provider_github_copilot")  # LINE 81
```
The actual module path is `amplifier_module_provider_github_copilot/` (no `src/` prefix). This test **always passes vacuously** because `root.glob("*.py")` finds zero files. The SDK import quarantine enforcement is completely untested.

**Gap — Ephemeral session invariants**: `test_session_config_exists` only instantiates `SessionConfig(model="gpt-4")` and checks attributes. It does not verify that `complete()` creates a new session per call, destroys sessions after turns, or prevents session reuse.

**Gap — Tool requests returned to orchestrator (NoExecution:MUST:2)**: No test exercises the path where `complete()` returns a response with tool calls that were captured from events rather than executed.

### 1.3 SDK Boundary (`contracts/sdk-boundary.md`)

**Excellent coverage** for the Config contract (MUST:1-6) — all six Config clauses have dedicated ConfigCapturingMock tests.

**Structural Mismatch — `sdk-boundary:Membrane:MUST:2`**: The contract says "MUST have exactly ONE file (`_imports.py`) that imports from `github_copilot_sdk`." The implementation has no `_imports.py`. SDK imports live in `client.py` directly. The contract and implementation are out of sync — either the contract needs updating or `_imports.py` needs to be created.

**Gap — Type boundary tests (Types:MUST:1,2,3)**: No tests verify that SDK types don't cross the boundary. These would be architecture fitness tests scanning for SDK type annotations in domain code.

### 1.4 Error Hierarchy (`contracts/error-hierarchy.md`)

**Excellent coverage** — all 7 MUST clauses are covered. This is the strongest contract coverage area.

Note: `test_error_translation.py` uses local `MockLLMError` classes (lines 23-74). These are not needed anymore — the real kernel types are imported directly. This dead code could be confusing.

### 1.5 Event Vocabulary (`contracts/event-vocabulary.md`)

**Good coverage** — all 6 MUST clauses covered.

Minor observation: `test_contract_events.py::TestDomainEventTypes::test_domain_event_dataclass_exists` passes `type="CONTENT_DELTA"` as a string but `DomainEvent.type` expects `DomainEventType` enum. This test works because Python dataclasses don't enforce types, but the test itself demonstrates the kind of loose typing that caused the F-044 bug — it's testing the wrong shape.

### 1.6 Streaming Contract (`contracts/streaming-contract.md`)

**Good coverage** for accumulation and tool capture.

**Gap — Circuit Breaker (CircuitBreaker:MUST:1)**: The contract references `config/retry.yaml::circuit_breaker.hard_turn_limit`. There's no test that verifies the provider raises `ProviderUnavailableError(retryable=False)` when turn count exceeds the hard limit. The streaming accumulator does not appear to track or enforce this limit.

**Amendment — `to_chat_response()` kernel type conversion**: The prior claim here was incorrect. `tests/test_f038_kernel_integration.py` includes dedicated tests for `StreamingAccumulator.to_chat_response()` returning a kernel `ChatResponse` and using both `TextBlock` and `ThinkingBlock`. Remaining gaps, if pursued, are narrower edge cases such as tool-call payloads, usage propagation, and empty-content behavior.

### 1.7 Behaviors Contract (`contracts/behaviors.md`)

**Zero coverage** — this entire contract is untested.

The behaviors contract defines:
- Retry policy (max_attempts, backoff, jitter, retryable flag, retry_after)
- Circuit breaker (soft/hard limits, ProviderUnavailableError at hard limit)
- Streaming timing warnings
- Model selection (aliases, NotFoundError for invalid models)

None of these have implementation tests. It's unclear whether these behaviors are even implemented (the behaviors contract has `[ ]` unchecked implementation checklist items).

---

## Section 2: Branch Coverage Analysis

### 2.1 `provider.py` — `extract_response_content()`

All 5 branches in the extraction priority chain are tested by `test_f043_sdk_response.py` (file exists but not fully read — based on contract coverage and feature spec).

Branches:
- `response is None` → return `""` ✅
- `hasattr(response, "data")` → recurse ✅  
- `hasattr(response, "content")` → extract ✅
- `isinstance(response, dict)` → get key ✅
- fallback → return `""` ✅

### 2.2 `provider.py` — `GitHubCopilotProvider.complete()`

**Two code paths, one under-tested and structurally unsafe:**

1. **Test injection path** (`sdk_create_fn is not None`) — tested via `sdk_create_fn` kwarg in test infrastructure
2. **Real SDK path** (`self._client.session()`) — **untested without live credentials and missing local error translation**

The real SDK path (lines 480-495) uses `send_and_wait()` with content extraction. It is not only a live-only branch with no unit test coverage; it also lacks a local `try/except` and does not call `translate_sdk_error(...)`, so raw SDK exceptions can escape the provider boundary. This is the dominant P0 bug tracked as **F-072**.

### 2.3 `provider.py` — `_load_models_config()`

Three branches:
- Config file doesn't exist → `_default_provider_config()` — likely tested by `test_config_loading.py`
- Config file parsing fails (exception) → `_default_provider_config()` — unclear if tested
- Config file empty → `_default_provider_config()` — unclear if tested

### 2.4 `error_translation.py` — `translate_sdk_error()`

**Strong branch coverage:**
- Mapping match by SDK type pattern ✅
- Mapping match by string pattern ✅
- First match wins ✅
- `extract_retry_after=True` ✅
- `InvalidToolCallError` special case (no `retry_after` arg) — ⚠️ one test exercises `InvalidToolCallError` in `test_f035_error_types.py` (not read, assumed from feature spec)
- No match → default fallback ✅

**Untested branch:** `_extract_context()` in F-036 path — context extraction via regex patterns. Test `test_f036_error_context.py` exists but wasn't read in full; likely covered.

### 2.5 `streaming.py` — `StreamingAccumulator.add()`

**Excellent branch coverage** in `test_streaming.py`:
- `CONTENT_DELTA` with `block_type == "THINKING"` ✅
- `CONTENT_DELTA` with other block_type ✅
- `CONTENT_DELTA` with `block_type is None` ✅
- `TOOL_CALL` ✅
- `USAGE_UPDATE` ✅
- `TURN_COMPLETE` ✅
- `ERROR` ✅

### 2.6 `client.py` — `CopilotClientWrapper.session()`

**Critical untested branches:**

```python
# Lines 182-214: Lazy client initialization
async with self._client_lock:
    client = self._get_client()
    if client is None:           # <-- untested when SDK installed
        try:
            from copilot import CopilotClient  # only in live tests
            ...
        except ImportError as e:  # ✅ tested by test_sdk_boundary.py
        except Exception as e:    # ❌ untested (SDK raises non-ImportError at start)
```

- Double-checked locking path (lock held, client already initialized) — ❌ untested
- Exception during `client.start()` translated to domain error — ❌ untested
- `disconnect()` fails during cleanup — ❌ untested (exception in finally block)

---

## Section 3: Error Path Coverage

### 3.1 Well-covered error paths
- SDK not installed → `ProviderUnavailableError` ✅
- Unknown SDK error → `ProviderUnavailableError` (default) ✅
- Auth error → `AuthenticationError` (retryable=False) ✅
- Rate limit with `retry_after` extraction ✅
- LLMError not double-wrapped in `complete()` ✅ (`test_sdk_boundary.py::TestDoubleTranslationGuard`)

### 3.2 Missing error path tests

| Error Path | Location | Risk |
|---|---|---|
| `session_factory returns None` | `provider.py::complete()` line 252 | LOW — tested in test_sdk_boundary.py (partial read) |
| `session.disconnect()` throws | `client.py` finally block | MEDIUM — silent warning, no test |
| `client.stop()` throws | `client.py::close()` | MEDIUM — silent warning, no test |
| `yaml.safe_load` fails for models.yaml | `provider.py::_load_models_config()` | LOW — falls back gracefully |
| `session config creation fails` | `client.py::session()` except on `create_session` | LOW — `translate_sdk_error` wraps it |
| Circuit breaker hard limit hit | `streaming.py` | HIGH — behavior undefined, possibly not implemented |
| `json.JSONDecodeError` in `parse_tool_calls` | `tool_parsing.py` line 68 | MEDIUM — only if LLM sends malformed JSON args |

---

## Section 4: SDK Boundary Tests — ConfigCapturingMock Evaluation

### 4.1 ConfigCapturingMock implementation quality

The `tests/fixtures/config_capture.py` implementation is **correct and well-designed**:

```python
class StrictSessionStub:
    """Strict stub that only exposes known SDK session methods."""
    def __init__(self):
        self.session_id = "mock-session-001"
        self._disconnect_mock = AsyncMock()
        self._hook_mock = MagicMock()

    async def disconnect(self): ...
    def register_pre_tool_use_hook(self, hook): ...
```

This is the right approach. Unlike `MagicMock()`, accessing undefined attributes on `StrictSessionStub` raises `AttributeError` rather than silently returning a new mock. The deep copy on line 66 (`copy.deepcopy(config)`) correctly captures the config state at call time, preventing later mutations from affecting the captured value.

### 4.2 ConfigCapturingMock usage in tests

`test_sdk_boundary_contract.py` uses `ConfigCapturingMock` correctly across all 7 test cases in `TestSessionConfigContract` and all parameterized tests in `TestConfigInvariants`. This is the F-046/F-047 architecture working as designed.

### 4.3 MagicMock without spec= usage (forgiveness problem)

**Problem locations:**

1. **`test_contract_protocol.py` lines 103-108**:
```python
tc1 = MagicMock()         # No spec= 
tc1.id = "call_1"
tc1.name = "read_file"
tc1.arguments = {"path": "test.py"}

response = MagicMock()    # No spec=
response.tool_calls = [tc1]
```
These mocks have no spec. If `parse_tool_calls()` accessed an attribute that doesn't exist on a real tool call object, the test would still pass (MagicMock returns another mock). This is lower risk since `parse_tool_calls` only accesses `.arguments`, `.id`, and `.name` — but the spec= protection is absent.

2. **`test_sdk_boundary.py::TestDenyHookOnWrapper` (lines 57-63)**:
```python
mock_session = MagicMock()
mock_session.register_pre_tool_use_hook = MagicMock()
mock_session.disconnect = AsyncMock()
mock_client = AsyncMock()
mock_client.create_session = AsyncMock(return_value=mock_session)
```
This is the **pre-F-046 pattern** — the mock accepts any call without validation. While `test_sdk_boundary_contract.py` now covers this more rigorously with `ConfigCapturingMock`, this test remains in the suite. It still passes even if the config sent to `create_session` is wrong, because `AsyncMock.create_session` accepts anything.

---

## Section 5: MagicMock `spec=` Usage Analysis

| Test File | Uses spec= | Risk |
|---|---|---|
| test_sdk_boundary_contract.py | N/A (ConfigCapturingMock) | ✅ None |
| test_contract_protocol.py | No | ⚠️ Medium — response and tool call mocks |
| test_sdk_boundary.py | No | ⚠️ Medium — pre-F-046 pattern persists |
| test_completion.py | Unknown | Needs review |
| test_provider.py | Unknown | Needs review |
| test_integration.py | Unknown | Needs review |

The main risk is `test_sdk_boundary.py::TestDenyHookOnWrapper` which validates `register_pre_tool_use_hook.assert_called_once()` but doesn't validate *what config was passed to create_session*. This is the forgiveness problem F-047 diagnosed — it proves the hook was called, not that the config was correct.

---

## Section 6: Integration vs. Unit Test Balance

### Current distribution (estimated from file names and content)

| Category | Files | Count | % |
|---|---|---|---|
| Unit tests | test_streaming.py, test_error_translation.py, test_tool_parsing.py, test_completion.py | ~4 core | ~15% |
| Contract/behavioral tests | test_contract_*.py (5 files), test_sdk_boundary_contract.py | 6 files | ~20% |
| SDK boundary/integration | test_sdk_boundary.py, test_sdk_client.py, test_sdk_assumptions.py | 3 files | ~10% |
| Feature tests (F-0xx) | test_f035_*, test_f036_*, test_f037_*, test_f038_*, test_f043_* | 5 files | ~17% |
| Live/integration | test_live_sdk.py, test_integration.py, test_foundation_integration.py | 3 files | ~10% |
| Misc/fixture tests | test_placeholder.py, test_entry_point.py, test_auth_token.py, etc. | ~10 files | ~28% |

**Assessment:** The balance is roughly 60/30/10 for unit/integration/live, which aligns with the test pyramid. However, the "unit" tests are actually behavioral tests against real config files. True isolation (using mock configs) is rare.

---

## Section 7: Test Quality — Behavior vs. Method Calls

### 7.1 Tests that verify behavior ✅

**`test_sdk_boundary_contract.py`** — Gold standard. Tests exact config values sent to SDK, not just that methods were called:
```python
assert config["available_tools"] == []  # F-045
assert config["system_message"]["mode"] == "replace"  # F-044
```

**`test_streaming.py`** — Tests actual accumulation output, not just that `add()` was called.

**`test_error_translation.py`** — Tests the translated error type, retryable flag, retry_after extraction, and exception chaining.

### 7.2 Tests that only verify method calls ⚠️

**`test_sdk_boundary.py::TestDenyHookOnWrapper`**:
```python
mock_session.register_pre_tool_use_hook.assert_called_once()
```
This proves the hook was *registered*, not that it *works* or was registered with a correct function. Combined with `MagicMock()` for the client, this test cannot catch F-044/F-045 class bugs.

**`test_contract_protocol.py::TestProtocolComplete::test_accepts_kwargs`**:
```python
has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD ...)
assert has_var_keyword
```
This tests the function signature, not the completion behavior. It would pass even if `complete()` threw an exception for all inputs.

### 7.3 Tests that test the framework (waste) ⚠️

**`test_streaming.py::TestDomainEventType::test_all_domain_types_exist`**:
```python
for type_name in expected_types:
    assert hasattr(DomainEventType, type_name)
```
This tests Python enum construction, not behavior. If `DomainEventType.CONTENT_DELTA` was missing, every test using it would fail anyway.

**`test_streaming.py::TestAccumulatedResponse::test_accumulated_response_defaults`**: Tests that a dataclass has the defaults it was defined with. Pure framework test.

---

## Section 8: Missing Tests Per Module

### 8.1 `provider.py`

| Missing Test | Priority | Why |
|---|---|---|
| `complete()` creates new session per call (two calls → two distinct sessions) | HIGH | deny-destroy:Ephemeral:MUST:1 |
| `complete()` session is destroyed after returning (disconnect called) | HIGH | deny-destroy:Ephemeral:MUST:2 |
| `complete()` state is not shared between calls | MEDIUM | deny-destroy:Ephemeral:MUST:4 |
| Additional `to_chat_response()` edge cases (tool calls, usage, empty content) | MEDIUM | deeper coverage beyond existing F-038 kernel conversion tests |
| `list_models()` with empty models config → fallback single model | LOW | edge case |
| `_load_models_config()` when YAML parse fails | LOW | error path |

### 8.2 `sdk_adapter/client.py`

| Missing Test | Priority | Why |
|---|---|---|
| Lock contention: two concurrent `session()` calls, only one `CopilotClient` created | MEDIUM | Race condition F-019 fix |
| `disconnect()` exception in finally block is suppressed (warning only) | MEDIUM | Error path |
| `close()` exception is suppressed (warning only) | LOW | Error path |
| `deny_permission_request()` returns `PermissionRequestResult` when SDK available | MEDIUM | F-033 |
| `deny_permission_request()` falls back to dict when SDK unavailable | MEDIUM | F-033 backward compat |

### 8.3 `streaming.py`

| Missing Test | Priority | Why |
|---|---|---|
| `to_chat_response()` with tool calls → correct `ToolCall` list | HIGH | Additional edge coverage beyond existing F-038 text/thinking conversion tests |
| `to_chat_response()` with usage → correct `Usage` object | MEDIUM | Additional edge coverage beyond existing F-038 conversion tests |
| `to_chat_response()` with no content → empty content list (not error) | MEDIUM | Edge case |
| Circuit breaker hard limit raises `ProviderUnavailableError` | HIGH | behaviors:CircuitBreaker:MUST:2 |

### 8.4 `error_translation.py`

| Missing Test | Priority | Why |
|---|---|---|
| `InvalidToolCallError` created without `retry_after` argument | LOW | Special case line 336 |
| `_extract_context()` with invalid regex pattern → silently skips | LOW | Error path |

### 8.5 Entire `contracts/behaviors.md` contract

| Missing Test | Priority | Why |
|---|---|---|
| Retry policy respects `max_attempts` | HIGH | behaviors:Retry:MUST:1 |
| Retry policy applies backoff with jitter | HIGH | behaviors:Retry:MUST:2 |
| Retry only for `retryable=True` errors | HIGH | behaviors:Retry:MUST:3 |
| `retry_after` honored when present | HIGH | behaviors:Retry:MUST:4 |
| Circuit breaker raises at `hard_turn_limit` | HIGH | behaviors:CircuitBreaker:MUST:2 |
| Model alias resolution | MEDIUM | behaviors:Models:MUST:1 |
| `NotFoundError` for invalid model | MEDIUM | behaviors:Models:MUST:2 |

---

## Section 9: Critical Bugs Found in Tests

### Bug 1: `TestArchitectureFitness` scans nonexistent path — ALWAYS PASSES VACUOUSLY

**File:** `tests/test_contract_deny_destroy.py`, line 81  
**Severity:** HIGH  
**Status:** Silent false positive  

```python
root = Path("src/amplifier_module_provider_github_copilot")  # WRONG PATH
for py_file in root.glob("*.py"):  # Finds ZERO files
```

The actual source is at `amplifier_module_provider_github_copilot/` (no `src/` prefix). This test passes because `glob("*.py")` yields nothing, so the violation list remains empty. The SDK import quarantine — one of the most important architecture constraints — has zero enforcement.

**Fix required:**
```python
root = Path("amplifier_module_provider_github_copilot")
```

### Bug 2: `test_contract_deny_destroy.py::TestDenyHookNotConfigurable` has subtle assertion logic

**File:** `tests/test_contract_deny_destroy.py`, lines 66-73  
**Severity:** MEDIUM  

```python
assert "deny" not in key_lower or "disable" not in key_lower
```

This is logically equivalent to `NOT (deny AND disable)` — it passes for any key that doesn't contain BOTH "deny" AND "disable". It would pass for `deny_execution=true`, `disable_hook=true`, or `allow_tool_execution=false`. Only `allow_tool_execution` is checked separately. The logic doesn't reliably catch the specific keys it intends to catch.

### Bug 3: `test_contract_events.py::TestDomainEventTypes::test_domain_event_dataclass_exists` passes wrong type

**File:** `tests/test_contract_events.py`, line 98  
**Severity:** LOW  

```python
event = DomainEvent(type="CONTENT_DELTA", data={"text": "test"})
```

`DomainEvent.type` is typed as `DomainEventType` (an enum), not `str`. This test creates a structurally incorrect object that would fail at runtime in production code. The test passes only because dataclasses don't enforce types.

---

## Section 10: Test Coverage Summary by Module

| Module | Contract | Unit Coverage | Branch Coverage | Error Path | Quality |
|---|---|---|---|---|---|
| `provider.py` | provider-protocol.md | 60% | 40% | 50% | Medium |
| `error_translation.py` | error-hierarchy.md | 90% | 85% | 80% | High |
| `streaming.py` | streaming-contract.md, event-vocabulary.md | 75% | 80% | 40% | High |
| `tool_parsing.py` | provider-protocol.md | 85% | 75% | 60% | High |
| `sdk_adapter/client.py` | sdk-boundary.md, deny-destroy.md | 70% | 35% | 30% | Medium |
| `behaviors` (unimplemented?) | behaviors.md | 0% | 0% | 0% | None |

---

## Section 11: Priority Action Items

### P0 — Fix Broken Tests (these tests give false confidence)

1. **Fix `test_no_sdk_imports_outside_adapter` path** — change `Path("src/amplifier_module_provider_github_copilot")` to `Path("amplifier_module_provider_github_copilot")`. The entire SDK import quarantine guarantee is invalid while this bug exists.

2. **Verify `sdk-boundary:Membrane:MUST:2`** — the contract says `_imports.py` must be the only SDK import file, but `_imports.py` doesn't exist. Either the contract is stale or the architecture drifted. Needs reconciliation.

### P1 — Critical Missing Behavioral Tests

3. **Ephemeral session tests** — Test that calling `complete()` twice creates two separate sessions, and that session is disconnected after each call. These are the core deny-destroy:Ephemeral invariants.

4. **`provider-protocol:complete:MUST:3` (session destruction)** — Add a test using `ConfigCapturingMock` that verifies `disconnect()` was called after `complete()` exits the session context manager.

5. **Behavioral tests for `contracts/behaviors.md`** — Add dedicated retry and circuit-breaker behavior tests. This aligns with new spec **F-090**.

### P2 — High-Value Missing Tests

6. **Circuit breaker test** — Test that exceeding `hard_turn_limit` raises `ProviderUnavailableError(retryable=False)`. This may reveal the circuit breaker is not yet implemented.

7. **Retry behavior tests** — Any test for the retry policy. These may also reveal that retry logic lives in the kernel (amplifier_core), not in this module — in which case, the `behaviors.md` contract may be aspirational.

8. **`provider-protocol:complete:MUST:4`** — Two sequential `complete()` calls with different prompts return independent responses (state isolation). This aligns with new spec **F-091**.

### P3 — Quality Improvements

9. **Replace `MagicMock()` with spec'd mocks in `test_sdk_boundary.py`** — The pre-F-046 `TestDenyHookOnWrapper` test should use `ConfigCapturingMock` or spec'd mocks to prevent silent forgiveness.

10. **Fix `test_contract_deny_destroy.py::TestDenyHookNotConfigurable` assertion logic** — The `or` logic doesn't catch what it intends to catch. Replace with explicit forbidden key list.

11. **Replace `MockLLMError` classes in `test_error_translation.py`** — These are dead code since F-038 imports real kernel types. Remove to reduce confusion.

---

## Appendix: Test File Inventory

| File | Purpose | Contract | Quality |
|---|---|---|---|
| test_auth_token.py | Auth token resolution | sdk-boundary | Not read |
| test_bug_fixes.py | Regression tests | Various | Not read |
| test_completion.py | Completion lifecycle | provider-protocol | Not read |
| test_concurrent_sessions.py | Concurrency | deny-destroy | Not read |
| test_config_loading.py | Config file loading | behaviors | Not read |
| test_contract_deny_destroy.py | Deny+Destroy pattern | deny-destroy | ⚠️ Bug in path |
| test_contract_errors.py | Error hierarchy | error-hierarchy | ✅ Good |
| test_contract_events.py | Event vocabulary | event-vocabulary | ✅ Good |
| test_contract_protocol.py | Provider protocol | provider-protocol | ⚠️ Shallow for complete() |
| test_contract_streaming.py | Streaming contract | streaming-contract | ✅ Good |
| test_deny_hook_breach_detector.py | Deleted | — | Tombstone only |
| test_entry_point.py | Module importability | — | Not read |
| test_ephemeral_session_wiring.py | Deleted | — | Tombstone only |
| test_error_translation.py | Error translation | error-hierarchy | ✅ Good |
| test_f035_error_types.py | F-035 feature | error-hierarchy | Not read |
| test_f036_error_context.py | F-036 context extraction | error-hierarchy | Not read |
| test_f037_observability.py | F-037 logging | tool_parsing | Not read |
| test_f038_kernel_integration.py | F-038 kernel types | streaming | ✅ Verified dedicated to_chat_response tests |
| test_f043_sdk_response.py | F-043 response extraction | sdk-response | Not read |
| test_foundation_integration.py | Kernel integration | provider-protocol | Not read |
| test_integration.py | End-to-end | All | Not read |
| test_live_sdk.py | Real API smoke tests | All | Requires credentials |
| test_permission_handler.py | Permission handler | deny-destroy | Not read |
| test_placeholder.py | — | — | Placeholder |
| test_protocol_compliance.py | Protocol compliance | provider-protocol | Not read |
| test_provider.py | Provider class | provider-protocol | Not read |
| test_sdk_adapter.py | SDK adapter | sdk-boundary | Not read |
| test_sdk_assumptions.py | SDK type assumptions | sdk-boundary | ✅ Good |
| test_sdk_boundary.py | SDK boundary | sdk-boundary | ⚠️ Pre-F-046 mocks |
| test_sdk_boundary_contract.py | Config contract | sdk-boundary | ✅ Excellent |
| test_sdk_client.py | Client wrapper | sdk-boundary | Not read |
| test_security_fixes.py | Security | sdk-boundary | Not read |
| test_session_factory.py | Session factory | deny-destroy | Not read |
| test_streaming.py | Streaming accumulator | streaming-contract | ✅ Excellent |
| test_tool_parsing.py | Tool parsing | provider-protocol | Not read |

---

*Analysis based on manual review of source code and tests as of 2026-03-14.*  
*Coverage percentages are estimates from reading code, not from a coverage tool run.*
