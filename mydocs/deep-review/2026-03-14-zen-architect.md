# Deep Architectural Review: Golden Vision V2 Compliance

**Reviewer**: Zen Architect  
**Date**: 2026-03-14  
**Scope**: Full codebase vs. Golden Vision V2 constitution  
**Verdict**: ⚠️ **Partial Compliance — Structurally Sound, Significant Gaps Remain**

---

## Executive Summary

The codebase has made meaningful progress toward the Golden Vision V2 architecture. The Three-Medium structure exists (Python + YAML + Markdown). The SDK boundary membrane is partially enforced. Config-driven error translation and event routing are implemented. However, several non-negotiable constraints from the constitution are violated, and the Python layer is ~81% over its target line count. The architecture is directionally correct but not yet compliant.

**Compliance Score: 6/10**

| Dimension | Score | Status |
|-----------|-------|--------|
| Three-Medium Architecture | 7/10 | ⚠️ Structure exists, balance off |
| Contract-First SDK Boundary | 5/10 | 🔴 SDK types leak through `Any` |
| Deny + Destroy Pattern | 8/10 | ⚠️ Implemented but dual-path fragility |
| Config-Driven Behavior | 7/10 | ⚠️ Good for errors/events, retry unused |
| Module Boundaries | 6/10 | ⚠️ provider.py is a monolith |
| Cyclomatic Complexity | 7/10 | ✅ Major reduction from 47 |
| Ruthless Simplicity | 5/10 | 🔴 Duplication and dead abstractions |

---

## 1. Three-Medium Architecture Compliance

**Golden Vision Requirement** (Principle 2):
> Python for mechanism (~300 lines irreducible logic), YAML for policy (~200 lines), Markdown for contracts (~400 lines).

### Current State

| Medium | Target | Actual | Delta |
|--------|--------|--------|-------|
| Python (mechanism) | ~670 lines | ~1,246 lines | **+86% over** |
| YAML (policy) | ~160 lines | ~213 lines | +33% (acceptable) |
| Markdown (contracts) | ~400 lines | 8 files (exists) | ✅ |

### Python Breakdown

| File | Lines | GV2 Target | Status |
|------|-------|------------|--------|
| `provider.py` | 532 | ~120 | 🔴 **4.4× over target** |
| `error_translation.py` | 382 | ~80 | 🔴 **4.8× over target** |
| `streaming.py` | 273 | ~100 | 🔴 **2.7× over target** |
| `tool_parsing.py` | 91 | ~120 | ✅ Under target |
| `sdk_adapter/client.py` | 268 | ~100 (session_factory) | 🔴 **2.7× over** |
| `sdk_adapter/types.py` | 32 | N/A | ✅ Minimal |
| `__init__.py` | 95 | N/A | ✅ Acceptable |

**Diagnosis**: `provider.py` at 532 lines is the worst offender. The Golden Vision specifies `provider.py` as a "thin orchestrator (~120 lines)" that delegates to specialized modules. Instead, it contains:
- Config loading logic (lines 61–118) — should be in `config.py`
- Response content extraction (lines 121–157) — should be in `sdk_adapter/`
- `CompletionRequest` and `CompletionConfig` dataclasses (lines 164–196) — should be in `_types.py`
- The entire `complete()` lifecycle function (lines 198–293) — should be in `completion.py`
- The `complete_and_collect()` convenience wrapper (lines 295–325) — should be in `completion.py`
- ChatRequest-to-prompt conversion (lines 443–458) — should be in `converters.py`

**The Golden Vision explicitly specifies** a separate `completion.py` (~150 lines) and `config.py` module. Neither exists. Their logic is inlined in `provider.py`.

### YAML Assessment

| File | Lines | Cap | Status |
|------|-------|-----|--------|
| `config/errors.yaml` | 93 | 50 | 🔴 **Over 50-line cap** |
| `config/events.yaml` | 46 | 50 | ✅ |
| `config/models.yaml` | 46 | 50 | ✅ |
| `config/retry.yaml` | 28 | 50 | ✅ |

**Note**: `config/errors.yaml` exceeds the Golden Vision's 50-line cap per config file (Principle 5). At 93 lines, it's nearly double. The F-036 context extraction patterns contribute ~15 lines — these are legitimate policy, but the file should be split or the cap reconsidered.

### Missing from Golden Vision Directory Structure

| Expected | Status |
|----------|--------|
| `modules/provider-core/completion.py` | 🔴 **MISSING** — inlined in provider.py |
| `modules/provider-core/_types.py` | 🔴 **MISSING** — types scattered |
| `modules/provider-core/config.py` | 🔴 **MISSING** — inlined in provider.py |
| `modules/provider-core/session_factory.py` | 🔴 **MISSING** — inlined in client.py |
| `config/circuit-breaker.yaml` | 🔴 **MISSING** — merged into retry.yaml |
| `config/observability.yaml` | 🔴 **MISSING** |

---

## 2. Contract-First SDK Boundary

**Golden Vision Non-Negotiable #1**:
> No SDK type crosses the adapter boundary. Domain code never imports from the SDK.

### Violations Found

**VIOLATION 1: `SDKSession = Any` is not a boundary**

`sdk_adapter/types.py` line 31:
```python
SDKSession = Any
```

This is declared as an "opaque type alias" but `Any` provides zero type safety. The Golden Vision specifies `SessionHandle` as "a UUID string, not an SDK session reference." Instead, the raw SDK session object crosses the boundary — `provider.py` line 267 calls `session.send_message()` directly on the SDK object, and `client.py` line 249 yields the raw SDK session.

**Impact**: Domain code (`provider.py` lines 481–495) directly manipulates SDK session internals:
```python
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```

This is the exact anti-pattern the Golden Vision warns against. The provider orchestrator is reaching through the membrane to call SDK methods.

**VIOLATION 2: `extract_response_content()` handles SDK types in domain code**

`provider.py` lines 121–157 contain logic that inspects SDK response objects using `hasattr(response, "data")` and `hasattr(response, "content")`. This is SDK-shape-aware code living outside the adapter layer.

**VIOLATION 3: `client.py` imports from `error_translation` (upward dependency)**

`sdk_adapter/client.py` line 23:
```python
from ..error_translation import ErrorConfig, ErrorMapping, translate_sdk_error
```

The Golden Vision dependency diagram shows imports flow DOWN only:
```
_types.py (leaf)
    │
    ├───┼───────────────┐
    ↓   ↓               ↓
  errors  converters  client/
          tool_parsing  session_factory
                        │
                        ↓
                    sdk_adapter/ (ONLY code that imports SDK)
```

`sdk_adapter/client.py` imports from `error_translation.py` (a sibling, not a child), violating the "never sideways between peers" rule. The adapter layer should translate errors internally or accept an error translator via injection.

**VIOLATION 4: Duplicate error config loading**

`_load_error_config_once()` in `client.py` (lines 72–113) duplicates the YAML parsing logic from `error_translation.py`'s `load_error_config()`. This is exactly the kind of entanglement the Golden Vision warns against — the adapter layer is reimplementing config loading instead of receiving a pre-loaded config.

---

## 3. Deny + Destroy Pattern

**Golden Vision Non-Negotiable #2 and #6**:
> preToolUse deny hook on every session. No exceptions. No configuration.  
> Deny + Destroy is NEVER configurable. This is mechanism, not policy. No YAML knob.

### Assessment: ⚠️ Implemented but Fragile

**Correctly implemented:**
- `create_deny_hook()` in `client.py` (line 34) returns a hardcoded deny response ✅
- `deny_permission_request()` in `client.py` (line 43) denies at permission layer ✅
- `DENY_ALL` constant is not configurable ✅
- No YAML knob exists for deny behavior ✅
- `available_tools = []` set on every session (`client.py` line 220) ✅
- `deny_permission_request` set at both client and session level ✅

**Concern: Dual-path session creation**

There are TWO session creation paths:

1. **Real SDK path** (`client.py` `session()` method, lines 157–256): Creates session with deny hook via `register_pre_tool_use_hook` (line 242) ✅
2. **Test injection path** (`provider.py` `complete()` function, lines 246–257): Creates session via `sdk_create_fn`, then conditionally registers deny hook only `if hasattr(session, "register_pre_tool_use_hook")` (line 256) ⚠️

The test path's conditional `hasattr` check means a mock session without `register_pre_tool_use_hook` will silently skip deny hook registration. This is a sovereignty gap — the Golden Vision says "No exceptions."

**Concern: Session not always destroyed**

In `provider.py` `complete()` (lines 286–292), session destruction is attempted in a `finally` block but uses `hasattr(session, "disconnect")` — if the session object doesn't have `disconnect`, it's silently leaked. The Golden Vision specifies: "Sessions MUST be ephemeral — create, use once, destroy."

---

## 4. Config-Driven Behavior

**Golden Vision Principle 3**:
> The provider separates mechanism from policy — but every extracted policy ships with a sensible default.

### What's Config-Driven (Good) ✅

| Policy | Config File | Consumed By |
|--------|-------------|-------------|
| Error mappings | `config/errors.yaml` | `error_translation.py` |
| Event classification | `config/events.yaml` | `streaming.py` |
| Provider metadata | `config/models.yaml` | `provider.py` |
| Retry/circuit breaker | `config/retry.yaml` | **NOBODY** 🔴 |

### What's Still Hardcoded (Bad) 🔴

**VIOLATION: `config/retry.yaml` is not consumed by any Python code**

The retry policy exists as YAML but no code reads it. Circuit breaker limits, backoff strategy, streaming thresholds — all defined in `retry.yaml` but unused. This is the Golden Vision anti-pattern of "Config without consumers."

Grep evidence — no Python file imports or references retry.yaml:
- `provider.py`: No retry logic at all
- `client.py`: No circuit breaker enforcement
- `streaming.py`: No ttft_warning or max_gap enforcement

**VIOLATION: Hardcoded policy values in Python**

| Value | Location | Should Be |
|-------|----------|-----------|
| `"gpt-4"` default model | `provider.py:241` | `config/models.yaml` defaults |
| `"gpt-4o"` default model | `provider.py:480` | `config/models.yaml` defaults |
| Token resolution priority | `client.py:125` | `config/models.yaml` credential_env_vars |

`provider.py` line 241 hardcodes `"gpt-4"` as session default:
```python
session_config = config.session_config or SessionConfig(model=request.model or "gpt-4")
```

But `config/models.yaml` line 22 says the default should be `gpt-4o`. These disagree — a classic config-code drift bug.

`client.py` lines 125–129 hardcode the token priority order:
```python
for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
```

But `config/models.yaml` lines 13–17 also define this:
```yaml
credential_env_vars:
  - COPILOT_AGENT_TOKEN
  - COPILOT_GITHUB_TOKEN
  - GH_TOKEN
  - GITHUB_TOKEN
```

Two sources of truth. The code doesn't read the config.

---

## 5. Module Boundaries and Coupling

**Golden Vision Principle 1**:
> The provider's job is translation. Every design decision must answer: "Does this add translation capability or framework complexity?"

### Coupling Analysis

`provider.py` imports from:
- `error_translation` (3 symbols)
- `sdk_adapter.client` (2 symbols)
- `sdk_adapter.types` (2 symbols)
- `streaming` (7 symbols)
- `tool_parsing` (1 symbol)
- `amplifier_core` (4 symbols)
- `yaml`, `pathlib`, `dataclasses`

**15 import sources** for a file that should be a "thin orchestrator." The Golden Vision specifies `provider.py` as ~120 lines that delegates to `completion.py`. Instead, it IS `completion.py`.

### Missing Modules

The Golden Vision specifies these as separate files:
- `completion.py` — LLM call lifecycle. Currently inlined as `complete()` and `complete_and_collect()` in `provider.py`.
- `session_factory.py` — Ephemeral session + deny hook. Currently split between `provider.py` (test path) and `client.py` (real path).
- `config.py` — YAML config loader + validation. Currently inlined as `_load_models_config()` in `provider.py` and duplicated in `client.py`.
- `_types.py` — Shared domain types. Currently `CompletionRequest`, `CompletionConfig`, `ProviderConfig` are all in `provider.py`.

---

## 6. Cyclomatic Complexity

**Golden Vision Context**:
> Original monolith: cyclomatic complexity of 47, 14 cross-cutting concerns.

### Current Assessment

The original monolith has been decomposed into 5 Python files + 1 adapter sub-package. This is a significant structural improvement. However:

- `provider.py` at 532 lines is still a pseudo-monolith containing 4+ responsibilities
- `error_translation.py` at 382 lines is well-structured but large
- `client.py` at 268 lines mixes session lifecycle, client lifecycle, config loading, and error config duplication

**Estimated cyclomatic complexity of `provider.py`**: ~15-20 (down from 47). The `complete()` method alone has 6 branch points. The `GitHubCopilotProvider.complete()` method adds another 8+ branches for request conversion, test-vs-real path, and response handling.

**Verdict**: Meaningful reduction from 47, but `provider.py` needs to be split to reach the Golden Vision's target of ~120 lines.

---

## 7. Ruthless Simplicity

**Golden Vision Kill List** and **Design Principles**:
> "Does this add translation capability or framework complexity? If the latter, remove it."

### Over-Engineering Found

**1. Dual completion paths create unnecessary complexity**

`provider.py` has THREE ways to complete:
- `complete()` module-level function (line 198) — streaming generator
- `complete_and_collect()` module-level function (line 295) — convenience wrapper
- `GitHubCopilotProvider.complete()` method (line 423) — class method that conditionally uses either

The class method then has TWO internal paths:
- Test path: calls `_complete_internal()` which calls `complete()`
- Real path: uses `self._client.session()` directly

This is 4 levels of indirection for what should be one path. The Golden Vision specifies a single `completion.py` module.

**2. `CompletionRequest` duplicates kernel `ChatRequest`**

`provider.py` defines `CompletionRequest` (line 164) with `prompt`, `model`, `tools`, etc. Then `GitHubCopilotProvider.complete()` (lines 438–458) converts `ChatRequest` → `CompletionRequest`. This intermediate type adds no value — the provider should work directly with `ChatRequest` and translate at the SDK boundary.

**3. `AccumulatedResponse` duplicates `ChatResponse`**

`streaming.py` defines `AccumulatedResponse` (line 54) and `StreamingAccumulator` (line 67) with nearly identical fields. Then `to_chat_response()` (line 109) converts one to the other. The accumulator should build `ChatResponse` directly.

**4. Config loading is duplicated**

Error config loading appears in THREE places:
- `error_translation.py` `load_error_config()` (line 145)
- `client.py` `_load_error_config_once()` (line 72) — reimplements the same logic
- `provider.py` `complete()` (line 238) — calls `load_error_config()`

---

## 8. Errata V2.1 Compliance

The Golden Vision V2.1 errata corrected 7 issues. Checking compliance:

| Erratum | Requirement | Status |
|---------|-------------|--------|
| E1: 4 methods + 1 property | `name`, `get_info`, `list_models`, `complete`, `parse_tool_calls` | ✅ Compliant |
| E2: `complete(request, **kwargs)` | No named `on_content` callback | ✅ Compliant |
| E3: `list[ToolCall]` return type | Not `ToolCallBlock` | ✅ Compliant |
| E4: No `ContentDelta` type | Use kernel content types | ✅ Uses `TextBlock`/`ThinkingBlock` |
| E5: Kernel error types | Not custom `CopilotXxxError` | ✅ Uses `amplifier_core.llm_errors.*` |
| E6: Package name convention | `amplifier-module-provider-github-copilot` | ✅ Package dir matches |
| E7: Entry points in pyproject.toml | `[project.entry-points."amplifier.modules"]` | ❓ Not verified |

---

## 9. Enforcement Framework Compliance

Cross-referencing against `specs/ENFORCEMENT-FRAMEWORK.md`:

| Standard | Requirement | Status |
|----------|-------------|--------|
| LOC: `provider.py` ≤200 | Hard limit 400 | 🔴 **532 lines — exceeds HARD LIMIT** |
| LOC: `error_translation.py` ≤160 | Hard limit 400 | ⚠️ 382 — under hard, over soft |
| LOC: `streaming.py` ≤160 | Hard limit 400 | ⚠️ 273 — under hard, over soft |
| Python ≤670 lines total (new) | Target | 🔴 ~1,246 lines (186% of target) |
| `config/models.yaml` exists | Required | ✅ |
| `config/retry.yaml` exists | Required | ✅ (but unused) |
| `config/circuit-breaker.yaml` | Required | 🔴 Missing (merged into retry) |
| No hardcoded policy in Python | Enforcement script | 🔴 Multiple violations |
| No MagicMock without spec= | Test standard | Not assessed (test files not in scope) |

---

## 10. Summary of Findings

### Critical Issues (Must Fix)

| # | Issue | Golden Vision Reference |
|---|-------|----------------------|
| **C1** | `provider.py` at 532 lines exceeds 400-line hard limit | Principle 5, Enforcement §3 |
| **C2** | `retry.yaml` exists but no code consumes it | Principle 3: mechanism with defaults |
| **C3** | SDK session object crosses boundary as `Any` | Non-Negotiable #1 |
| **C4** | Hardcoded model defaults disagree with config (`gpt-4` vs `gpt-4o`) | Anti-pattern: Config-code drift |
| **C5** | `completion.py` doesn't exist — inlined in provider.py | Architecture §: Directory Structure |

### Significant Issues (Should Fix)

| # | Issue | Golden Vision Reference |
|---|-------|----------------------|
| **S1** | Duplicate error config loading in `client.py` | Anti-pattern: DRY violation |
| **S2** | `CompletionRequest` is unnecessary intermediate type | Principle 1: Translation, Not Framework |
| **S3** | Token env var priority hardcoded AND in config (two sources of truth) | Principle 2: YAML for policy |
| **S4** | `errors.yaml` exceeds 50-line config cap | Principle 5: Module size limits |
| **S5** | Dependency direction violation: `sdk_adapter/` → `error_translation` | Architecture §: Dependency Rules |

### What's Working Well ✅

1. **Error translation is genuinely config-driven** — `errors.yaml` mappings drive `translate_sdk_error()` with no hardcoded SDK-to-domain mapping in the Python code
2. **Event routing is config-driven** — `events.yaml` BRIDGE/CONSUME/DROP classification works correctly
3. **Kernel types are used** — E5 erratum is fully addressed; all errors use `amplifier_core.llm_errors.*`
4. **Deny hook is not configurable** — `DENY_ALL` is a hardcoded constant, no YAML knob exists
5. **`available_tools = []`** — Correctly disables SDK built-in tools on every session
6. **Contract references in docstrings** — Most modules cite their contract file
7. **`tool_parsing.py` is exemplary** — 91 lines, single responsibility, clean delegation

---

## 11. Recommended Next Steps (Priority Order)

1. **Extract `completion.py`** from `provider.py` — move `complete()`, `complete_and_collect()`, `CompletionRequest`, `CompletionConfig`, `extract_response_content()` to a separate module. Target: `provider.py` ≤200 lines.

2. **Wire `retry.yaml`** — the config file exists but is dead. Either consume it in the completion/session lifecycle or remove it (honesty > aspirational files).

3. **Fix model default inconsistency** — `provider.py:241` says `gpt-4`, `config/models.yaml` says `gpt-4o`. Read the default from config.

4. **Eliminate duplicate config loading** — `client.py._load_error_config_once()` should call `error_translation.load_error_config()`, not reimplement it.

5. **Fix dependency direction** — `sdk_adapter/client.py` should not import from `error_translation`. Inject the error config or error translator from the provider level.

6. **Replace `SDKSession = Any`** with a proper opaque handle (UUID string per Golden Vision spec).

---

*"The structure is there. The intent is clear. The execution needs one more extraction pass to reach the Golden Vision's target. The hardest part — config-driven error/event translation using kernel types — is done right. Now finish the decomposition."*

---

**Document Control**

| Field | Value |
|-------|-------|
| Reviewer | Zen Architect |
| Date | 2026-03-14 |
| Files Analyzed | 9 Python files, 4 YAML configs, 8 contracts, 2 spec documents |
| Golden Vision Version | V2.1 (Kernel-Validated) |
| Total Lines Reviewed | ~2,200 |
