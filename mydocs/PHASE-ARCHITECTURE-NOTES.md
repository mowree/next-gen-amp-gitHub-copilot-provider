# Phase-by-Phase Architectural Implementation Notes

**Authority:** Zen Architect — derived from AMPLIFIER-DIRECTIVE-2026-03-15.md + GOLDEN_VISION_V2.md
**Date:** 2026-03-15
**Purpose:** Architectural guidance for the autonomous dev-machine across all 9 phases

---

## Governing Invariants (All Phases)

These invariants MUST hold at the end of every phase. If any phase breaks one, that phase is incomplete.

| ID | Invariant | Medium | Enforcement |
|----|-----------|--------|-------------|
| INV-1 | Deny hook installed on every SDK session | Python (mechanism) | Architecture test + contract test |
| INV-2 | Sessions are ephemeral — create, use once, destroy | Python (mechanism) | Contract: `contracts/deny-destroy.md` |
| INV-3 | No SDK type crosses the adapter boundary | Python (structure) | Architecture fitness test |
| INV-4 | All tests pass after every feature | All | CI gate |
| INV-5 | Contracts have correct module reference paths | Markdown | Grep verification |
| INV-6 | Config loads from inside the wheel (after Phase 2) | YAML + Python | Import-time test |
| INV-7 | Error translation uses kernel types, not custom types | Python + YAML | `amplifier_core.llm_errors.*` only |

---

## Phase 0: Pre-Implementation Hygiene

**Architectural Goal:** Establish a clean, truthful baseline — no orphan directories, no stale paths, no misleading STATE.yaml blockers. The Three-Medium Architecture requires all three mediums to agree on reality before any feature work begins.

**Entry Conditions:**
- Repository is on `main` branch, all existing tests pass
- AMPLIFIER-DIRECTIVE-2026-03-15.md exists and has been read

**Exit Conditions:**
- `src/` directory deleted (only contained orphan `__pycache__/`)
- All 6 contract files in `contracts/` have correct module reference paths (no `src/` prefix, no `modules/provider-core/`)
- Spec amendments applied: F-072 (type fix), F-073 (type fix), F-052 (verified pattern), F-049 (expanded scope), F-071 (superseded marker)
- STATE.yaml blockers replaced with single directive reference
- STATE.yaml feature statuses updated per directive Part 6
- Tombstone files created: `F-041-RESERVED.md`, `F-042-RESERVED.md`

**Key Invariants to Preserve:**
- INV-4: All tests must still pass after path changes
- INV-5: Contract module references must match actual filesystem

**Architectural Risks:**
- **Risk:** Changing contract paths breaks contract compliance tests that parse those paths → **Mitigation:** Run full test suite after each contract file edit
- **Risk:** Deleting `src/` while tests reference it → **Mitigation:** F-049 fixes test paths in the same atomic operation

**Feature Implementation Notes:**

*No feature implementations — this is a manual preparation phase.*

---

## Phase 1: Zero-Risk Cleanups + Sovereignty Foundation

**Architectural Goal:** Establish the sovereignty invariant (deny hook enforcement) and clean up structural debt. In Three-Medium terms: fix the Markdown contracts (paths), establish the Python mechanism (deny hook), and remove dead code. This phase makes the codebase truthful before any behavioral changes.

**Entry Conditions:**
- Phase 0 complete — `src/` deleted, contract paths fixed, spec amendments applied
- All tests pass on clean baseline

**Exit Conditions:**
- Architecture tests use correct paths and pass
- Deny hook is mandatory — cannot create a session without it
- Tombstone test files deleted
- `py.typed` marker exists for type checker support
- Redundant `Path` import removed from provider.py
- All tests pass

**Key Invariants to Preserve:**
- INV-1: Deny hook installed on every session (F-050 ESTABLISHES this — most critical feature in Phase 1)
- INV-3: No SDK type crosses boundary
- INV-4: All tests pass
- INV-5: Contract paths correct (established in Phase 0, verified here)

**Architectural Risks:**
- **Risk:** F-050 deny hook enforcement could break existing test mocks that create sessions without hooks → **Mitigation:** Audit all test session creation; update mocks to include deny hook
- **Risk:** F-049 path changes are incomplete, leaving some `src/` references → **Mitigation:** grep -r verification as exit gate

**Feature Implementation Notes:**

### F-049: Fix Architecture Test Paths
- **Architectural Impact:** Markdown medium — corrects contracts to reflect actual filesystem; Python medium — fixes test assertions
- **Integration Points:** `tests/test_contract_deny_destroy.py` (line 81), `tests/test_sdk_client.py` (line 191), all 6 `contracts/*.md` files
- **Recommended Pattern:** Search-and-replace `src/amplifier_module_provider_github_copilot` → `amplifier_module_provider_github_copilot` in both test files and contract files. Special case: `contracts/deny-destroy.md` changes `modules/provider-core/session_factory.py` → `amplifier_module_provider_github_copilot/sdk_adapter/client.py`

### F-050: Mandatory Deny Hook Installation
- **Architectural Impact:** Python mechanism — this is the sovereignty invariant. Per GOLDEN_VISION_V2: "preToolUse deny hook on every session. No exceptions. No configuration." This is NON-NEGOTIABLE mechanism, never YAML policy.
- **Integration Points:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py` — session creation path. All tests that create SDK sessions.
- **Recommended Pattern:** Add a validation check in the session creation path that raises `ConfigurationError` if the deny hook is not installed. The check must be in the mechanism layer (Python), NOT configurable via YAML. Reference: `contracts/deny-destroy.md`

### F-077: Delete Tombstone Test Files
- **Architectural Impact:** None — pure cleanup. Removes dead files that confuse AI agents scanning the test directory.
- **Integration Points:** None
- **Recommended Pattern:** Delete identified tombstone files. Verify no imports reference them.

### F-079: Add py.typed Marker
- **Architectural Impact:** Packaging — enables downstream type checking. Part of the "AI-Maintainability as First-Class Goal" principle.
- **Integration Points:** `amplifier_module_provider_github_copilot/py.typed` (new empty file), `pyproject.toml` (may need package-data entry)
- **Recommended Pattern:** Create empty `py.typed` file in package root. Verify `pyproject.toml` includes it in package data.

### F-084: Remove Redundant Path Import
- **Architectural Impact:** None — pure cleanup in `provider.py`
- **Integration Points:** `amplifier_module_provider_github_copilot/provider.py`
- **Recommended Pattern:** Remove unused `from pathlib import Path` import. Verify with pyright/ruff.

---

## Phase 2: Config Foundation

**Architectural Goal:** Make the YAML policy medium functional and correct. The Three-Medium Architecture cannot work if config files aren't loadable from the installed wheel. This phase fixes the config pipeline so that all subsequent phases can rely on YAML-driven behavior.

**Entry Conditions:**
- Phase 1 complete — deny hook enforced, paths correct
- All tests pass

**Exit Conditions:**
- Config files (`config/`) are included in the wheel package
- `_load_error_config_once()` correctly parses `context_extraction` field
- Fallback `ProviderInfo` includes `defaults.context_window`
- Config loads correctly when package is installed (not just in dev mode)

**Key Invariants to Preserve:**
- INV-1: Deny hook still installed (no config makes this optional)
- INV-4: All tests pass
- INV-6: Config loads from inside the wheel (ESTABLISHED by F-074)
- INV-7: Error translation uses kernel types

**Architectural Risks:**
- **Risk:** F-074 changes config loading paths, breaking all config-dependent code → **Mitigation:** Use `importlib.resources` for package-relative config access. Test with both `pip install -e .` and `pip install .`
- **Risk:** F-081 context_extraction fix changes ErrorMapping dataclass, breaking existing error translation → **Mitigation:** Add field with default `[]` to preserve backward compatibility

**Feature Implementation Notes:**

### F-074: Config Not in Wheel
- **Architectural Impact:** YAML medium — this is the foundation for all config-driven features. Without this, the Three-Medium Architecture's YAML layer is broken in production. Every subsequent config feature (F-060, F-061, F-066, F-068) depends on this.
- **Integration Points:** `pyproject.toml` (package-data or include), config loader in `sdk_adapter/client.py` or separate `config.py`, all code that calls `Path(__file__).parent.parent / "config"` pattern
- **Recommended Pattern:** Use `importlib.resources` (Python 3.11+) to load YAML files from within the package. Move `config/` under `amplifier_module_provider_github_copilot/config/` OR add it to `pyproject.toml` package data. The loader must work in both editable and installed modes.

### F-081: Fix context_extraction in Client Error Loading
- **Architectural Impact:** YAML medium — restores the bridge between `config/errors.yaml` context_extraction declarations and the Python mechanism that uses them. F-036 (completed) added context_extraction to the config; this fix makes it actually load.
- **Integration Points:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py` lines 86-98 — `_load_error_config_once()` function
- **Recommended Pattern:** Add `context_extraction=mapping_data.get("context_extraction", [])` to the `ErrorMapping()` constructor call. Verify `ErrorMapping` dataclass has the field.

### F-078: Add context_window to Fallback Config
- **Architectural Impact:** YAML medium — completes the model capabilities config. Kernel contract requires `ProviderInfo.defaults.context_window`.
- **Integration Points:** Wherever `ProviderInfo` is constructed with fallback/default values
- **Recommended Pattern:** Add `context_window: 128000` (or appropriate value for GPT-4o) to the fallback configuration.

---

## Phase 3: P0 Critical Path — SDK Integration Correctness

**Architectural Goal:** Close the most dangerous gap in the SDK boundary membrane: raw SDK exceptions escaping the provider. In Three-Medium terms, this phase wires the Python mechanism to the YAML policy for error translation on the real SDK path, and adds the streaming pipeline that the SDK actually supports.

**Entry Conditions:**
- Phase 2 complete — config loads from wheel
- F-074 verified (config accessible)
- All tests pass

**Exit Conditions:**
- Real SDK path in `provider.py` has try/except with `translate_sdk_error()`
- Tests verify error translation on the real SDK path
- Real SDK streaming pipeline implemented using verified `on()` + queue pattern
- Event config loading is defensive (handles missing/malformed YAML)
- No raw SDK exceptions can escape `complete()`

**Key Invariants to Preserve:**
- INV-1: Deny hook installed on every session
- INV-3: No SDK type crosses boundary — translated errors must be kernel types
- INV-6: Config loads from wheel
- INV-7: Error translation uses kernel types (ProviderUnavailableError, NOT LLMProviderError)

**Architectural Risks:**
- **Risk:** F-072 error translation wraps the wrong code path → **Mitigation:** Directive provides exact line numbers (provider.py 479-495). The `else:` branch (real SDK path) is the target.
- **Risk:** F-052 streaming pattern doesn't work with actual SDK version → **Mitigation:** Pattern verified against `copilot-sdk/python/e2e/test_streaming_fidelity.py`. Use `SessionEventType` enum, not string comparisons.
- **Risk:** F-052 introduces a second streaming path alongside the existing one → **Mitigation:** The existing path is mock/fallback; F-052 adds the real SDK path. Both coexist, selected by SDK mode.

**Feature Implementation Notes:**

### F-072: Real SDK Path Error Translation
- **Architectural Impact:** Python mechanism — closes the most critical gap in the SDK boundary membrane. Without this, any SDK exception escapes raw into the kernel, violating `contracts/provider-protocol.md` and `contracts/error-hierarchy.md`.
- **Integration Points:** `amplifier_module_provider_github_copilot/provider.py` lines 479-495 (the `else:` branch), `error_translation.py` (`translate_sdk_error`), `config/errors.yaml`
- **Recommended Pattern:** Wrap the `async with self._client.session(...)` block in `try/except Exception as e:`, call `translate_sdk_error(e, error_config, provider="github-copilot", model=model)`, re-raise the translated error. The fallback type is `ProviderUnavailableError` — NOT `LLMProviderError` (does not exist).
- **IMPLEMENT FIRST in this phase.**

### F-073: Real SDK Path Error Test
- **Architectural Impact:** Test tier — verifies F-072's mechanism. Contract-anchored to `contracts/error-hierarchy.md`.
- **Integration Points:** New test file or addition to existing error translation test file
- **Recommended Pattern:** Mock `sdk_session.send_and_wait()` to raise various exceptions. Assert each maps to the correct kernel error type. Key case: `RuntimeError` → `ProviderUnavailableError` (fallback).
- **IMPLEMENT AFTER F-072.**

### F-052: Real SDK Streaming Pipeline
- **Architectural Impact:** Python mechanism — implements the actual streaming translation using SDK's `on()` callback pattern. This is the core of the Three-Medium Architecture's Python layer: mechanical translation of SDK events → domain events.
- **Integration Points:** `amplifier_module_provider_github_copilot/provider.py` (new streaming path), `streaming.py` (accumulator), SDK types: `SessionEventType.ASSISTANT_MESSAGE_DELTA`, `ASSISTANT_MESSAGE`, `SESSION_IDLE`, `SESSION_ERROR`
- **Recommended Pattern:** Use the verified `asyncio.Queue` + `on()` handler pattern from directive Part 3.3. Wire queue events to `StreamEvent` domain types. Include timeout on `queue.get()` for safety.

### F-051: Defensive Event Config Loading
- **Architectural Impact:** Python mechanism + YAML policy — makes the event config loading path robust against missing or malformed `config/events.yaml`. Without this, a broken YAML file crashes the provider at startup.
- **Integration Points:** Event config loader, `config/events.yaml`
- **Recommended Pattern:** Try/except around YAML load with fallback to hardcoded defaults. Log a warning when falling back. This preserves the Three-Medium Architecture's principle: "Mechanism with Sensible Defaults."

---

## Phase 4: Robustness Hardening

**Architectural Goal:** Harden the SDK boundary membrane against edge cases: timeouts, resource leaks, recursion, and incomplete accumulation. In Three-Medium terms, this strengthens the Python mechanism layer to handle real-world failure modes that the YAML policy layer cannot address.

**Entry Conditions:**
- Phase 3 complete — error translation works on real SDK path, streaming pipeline functional
- All tests pass

**Exit Conditions:**
- Timeouts enforced on real SDK path (`asyncio.wait_for` or equivalent)
- `provider.close()` delegates to `client.close()` (no more resource leak)
- Error config loading is unified (single code path)
- Response extraction has recursion guard
- Streaming accumulator has completion guard
- SDK client handles failed start gracefully

**Key Invariants to Preserve:**
- INV-1: Deny hook installed
- INV-2: Sessions are ephemeral (F-082 strengthens this — close actually cleans up)
- INV-3: No SDK type crosses boundary
- INV-7: Error translation uses kernel types

**Architectural Risks:**
- **Risk:** F-085 timeout enforcement wraps too much code, catching non-timeout exceptions as timeouts → **Mitigation:** Use `asyncio.wait_for()` specifically on `send_and_wait()`, not on the entire completion flow
- **Risk:** F-082 wiring close() creates double-close bugs → **Mitigation:** `client.close()` already handles idempotent close (`if self._owned_client is not None`)
- **Risk:** F-053 config unification changes error mapping behavior → **Mitigation:** Run error translation tests before and after; behavior must be identical

**Feature Implementation Notes:**

### F-085: Timeout Enforcement on Real SDK Path (absorbs F-058)
- **Architectural Impact:** Python mechanism — adds the missing timeout boundary. Per GOLDEN_VISION_V2, timeout values are YAML policy; timeout enforcement is Python mechanism.
- **Integration Points:** `provider.py` real SDK path (the try/except added by F-072), `config/retry.yaml` for timeout values
- **Recommended Pattern:** `await asyncio.wait_for(sdk_session.send_and_wait(...), timeout=configured_timeout)`. Catch `asyncio.TimeoutError`, translate to `LLMTimeoutError`.

### F-082: Wire provider.close() to client.close()
- **Architectural Impact:** Python mechanism — closes a resource leak. The provider's `close()` is a no-op (lines 517-523) while `client.close()` has working cleanup (lines 258-268).
- **Integration Points:** `provider.py` `close()` method, `self._client.close()`
- **Recommended Pattern:** `await self._client.close()` in `provider.close()`. Add try/except for resilience.

### F-053: Unify Error Config Loading
- **Architectural Impact:** Python mechanism — eliminates duplicate config loading paths. Currently `error_translation.py` and `sdk_adapter/client.py` each have their own loader.
- **Integration Points:** `error_translation.py`, `sdk_adapter/client.py`, potentially new shared config loader
- **Recommended Pattern:** Single `_load_error_config()` function called once at startup, result cached. Both modules reference the same loaded config.

### F-054: Response Extraction Recursion Guard
- **Architectural Impact:** Python mechanism — prevents infinite recursion in `extract_response_content()` if SDK returns nested Data objects.
- **Integration Points:** Response extraction function in `provider.py`
- **Recommended Pattern:** Add `max_depth` parameter (default 3). Return string representation if depth exceeded.

### F-055: Streaming Accumulator Completion Guard
- **Architectural Impact:** Python mechanism — prevents accumulator from accepting events after completion signal.
- **Integration Points:** `streaming.py` accumulator
- **Recommended Pattern:** Boolean `_completed` flag, set on `TURN_COMPLETE` / `SESSION_IDLE`. Reject further events with warning log.

### F-056: SDK Client Failed Start Cleanup
- **Architectural Impact:** Python mechanism — ensures resources are cleaned up if SDK subprocess fails to start.
- **Integration Points:** `sdk_adapter/client.py` startup path
- **Recommended Pattern:** try/except around subprocess start. In except block, clean up any partially-initialized resources before re-raising.

---

## Phase 5: Error & Integration Refinement

**Architectural Goal:** Complete the error translation system and add multi-turn context support. In Three-Medium terms, this enriches the YAML policy layer (new error mappings, event validation) and extends the Python mechanism (multi-turn, disconnect handling).

**Entry Conditions:**
- Phase 4 complete — timeout, close, recursion guard, accumulator guard all in place
- Error config loads from unified path
- All tests pass

**Exit Conditions:**
- Error matching algorithm is safe against edge cases (F-066)
- Missing error mappings added to `config/errors.yaml` (F-061)
- Event classification validates against overlap/gaps (F-068)
- `ChatRequest` supports multi-turn conversation context (F-059)
- Session disconnect failures are handled gracefully (F-086)

**Key Invariants to Preserve:**
- INV-1: Deny hook installed
- INV-3: No SDK type crosses boundary
- INV-6: Config loads from wheel
- INV-7: Error translation uses kernel types

**Architectural Risks:**
- **Risk:** F-066 changes the error matching algorithm, changing which errors get classified how → **Mitigation:** F-066 MUST come before F-061. Fix the algorithm first, then add mappings.
- **Risk:** F-059 multi-turn context passes conversation history through the SDK boundary → **Mitigation:** History must be domain types (not SDK types) until the adapter layer converts them. INV-3 enforced.

**Feature Implementation Notes:**

### F-066: Error Translation Safety
- **Architectural Impact:** Python mechanism — fixes the error matching algorithm to handle edge cases safely. This MUST land before F-061 adds new mappings.
- **Integration Points:** `error_translation.py` matching logic
- **Recommended Pattern:** Ensure pattern matching is case-insensitive, handles inheritance, and has explicit fallback. Test with adversarial inputs (empty strings, None, nested exceptions).

### F-061: Error Config Missing Mappings
- **Architectural Impact:** YAML policy — adds mappings that `config/errors.yaml` is missing relative to `contracts/error-hierarchy.md`. Pure YAML edit if all kernel error types are already supported.
- **Integration Points:** `config/errors.yaml`, contract: `contracts/error-hierarchy.md`
- **Recommended Pattern:** Add missing `sdk_patterns` entries. Each must map to a kernel type from `amplifier_core.llm_errors`. Add config compliance test for each new mapping.

### F-068: Event Classification Validation
- **Architectural Impact:** YAML policy + Python verification — validates `config/events.yaml` has no overlapping or gap classifications. Enforces the Three-Medium Architecture's contract: "Every SDK event is classified as BRIDGE, CONSUME, or DROP."
- **Integration Points:** `config/events.yaml`, test that validates completeness
- **Recommended Pattern:** Test that loads events.yaml and verifies: (1) no SDK event type appears in more than one category, (2) known SDK event types are all classified.

### F-059: ChatRequest Multi-Turn Context
- **Architectural Impact:** Python mechanism — extends the completion flow to pass conversation history. This is a protocol-level enhancement.
- **Integration Points:** `provider.py` `complete()` method, `ChatRequest` type, SDK session `send()` call
- **Recommended Pattern:** Accept `messages` list in `ChatRequest`. Convert domain messages to SDK format in the adapter layer. INV-3: conversion happens inside the SDK boundary.

### F-086: Handle Session Disconnect Failures
- **Architectural Impact:** Python mechanism — makes session cleanup resilient. Currently disconnect failures may be swallowed silently or crash.
- **Integration Points:** Session teardown in `sdk_adapter/client.py`
- **Recommended Pattern:** try/except around `session.disconnect()`. Log warning on failure. Never let disconnect failure mask the primary result/error.

---

## Phase 6: Retry System

**Architectural Goal:** Implement config-driven retry as a clean Three-Medium feature: retry POLICY in YAML, retry MECHANISM in Python, retry CONTRACT in Markdown. This phase also cleans up dead retry config and adds behavioral tests.

**Entry Conditions:**
- Phase 5 complete — error system is complete and safe
- Error mappings include `retryable` field (from F-061)
- All tests pass

**Exit Conditions:**
- Dead `retry.yaml` config removed (if it exists with unused content)
- Config-driven retry implemented using `config/retry.yaml` parameters
- Behavioral tests verify retry behavior matches `contracts/behaviors.md`

**Key Invariants to Preserve:**
- INV-1: Deny hook installed (retry must not bypass sovereignty)
- INV-2: Sessions are ephemeral (each retry creates a NEW session, not reuses)
- INV-7: Retried errors use kernel types

**Architectural Risks:**
- **Risk:** Retry creates a "Two Orchestrators" problem — provider retries conflict with kernel orchestrator retries → **Mitigation:** Per GOLDEN_VISION_V2: "The provider does not manage retry logic (kernel policy)." If the kernel already retries, the provider should NOT. Verify against kernel contracts before implementing.
- **Risk:** Retry reuses sessions, violating ephemeral invariant → **Mitigation:** Each retry attempt must go through full session create/use/destroy cycle.

**Feature Implementation Notes:**

### F-075: Delete Dead Retry YAML Config
- **Architectural Impact:** YAML policy cleanup — remove config that nothing reads. Must happen BEFORE F-060 to avoid confusion about which config is active.
- **Integration Points:** `config/retry.yaml` (inspect for dead sections)
- **Recommended Pattern:** Identify unused config keys via grep. Remove them. Keep the file structure clean for F-060.

### F-060: Config-Driven Retry
- **Architectural Impact:** Three-Medium exemplar — this is the cleanest example of the architecture: `contracts/behaviors.md` specifies retry requirements, `config/retry.yaml` declares retry parameters, Python code reads config and executes the retry loop.
- **Integration Points:** `config/retry.yaml`, `provider.py` or new `retry.py`, `error_translation.py` (retryable field)
- **Recommended Pattern:** Load retry config at startup. Implement exponential backoff with jitter per config. Only retry errors where `retryable=True` per error mapping. Cap at `max_attempts` from config. **CRITICAL:** Verify this doesn't duplicate kernel-level retry. If kernel retries, this may be a no-op.

### F-090: Behavioral Tests for Behaviors Contract
- **Architectural Impact:** Test tier — contract compliance tests for `contracts/behaviors.md`. These verify the Python mechanism matches the Markdown contract.
- **Integration Points:** `contracts/behaviors.md`, test file
- **Recommended Pattern:** One test per MUST clause in the behaviors contract. Each test cites the specific clause it verifies.

---

## Phase 7: Structural Refactoring

**Architectural Goal:** Refactor the codebase structure to better match the Three-Medium Architecture's target layout. Create the SDK import quarantine (`_imports.py`), align types to contracts, remove dead code, and improve test quality — all before the major provider decomposition in Phase 8.

**Entry Conditions:**
- Phase 6 complete — retry system in place
- All features that modify `provider.py` behavior (F-052, F-054, F-059, F-072, F-082, F-085) are done
- All tests pass

**Exit Conditions:**
- `_imports.py` exists as SDK import quarantine
- SDK boundary structure extended via F-063
- Dead `complete_fn` code removed
- Deferred imports cleaned up
- `SessionConfig` shape aligns with contract
- `complete` parameter type strengthened
- Test quality improved (F-067)
- All tests pass

**Key Invariants to Preserve:**
- INV-1: Deny hook installed
- INV-3: No SDK type crosses boundary (F-088 STRENGTHENS this — all SDK imports via `_imports.py`)
- INV-4: All tests pass (refactoring must not change behavior)

**Architectural Risks:**
- **Risk:** F-088 `_imports.py` quarantine changes import paths, breaking existing code → **Mitigation:** Re-export everything from `_imports.py` that was previously imported directly. Then update consumers one at a time.
- **Risk:** F-089 SessionConfig changes break session creation → **Mitigation:** Run session creation tests after each field change. Use dataclass defaults for backward compatibility.
- **Risk:** F-069 removes code that appears dead but is called via dynamic dispatch → **Mitigation:** Use LSP `findReferences` to verify `complete_fn` has zero callers before removing.

**Feature Implementation Notes:**

### F-067: Test Quality Improvements
- **Architectural Impact:** Test tier — improves test reliability and clarity. Moved from Phase 9 to Phase 7 because test quality must be high BEFORE F-065 provider decomposition.
- **Integration Points:** Multiple test files
- **Recommended Pattern:** Fix flaky tests, improve assertion messages, add missing contract citations, ensure test isolation.

### F-088: Create _imports.py SDK Quarantine
- **Architectural Impact:** Python structure — strengthens INV-3 by creating a single file that all SDK imports pass through. This is the architectural enforcement mechanism for "no SDK type crosses the boundary."
- **Integration Points:** `amplifier_module_provider_github_copilot/sdk_adapter/_imports.py` (new), all files in `sdk_adapter/` that import from SDK
- **Recommended Pattern:** Create `_imports.py` that imports all needed SDK types and re-exports them. Update all `sdk_adapter/` files to import from `_imports.py` instead of directly from SDK. Architecture test verifies no other file imports SDK directly.
- **IMPLEMENT FIRST in this phase (F-063 depends on it).**

### F-063: SDK Boundary Structure
- **Architectural Impact:** Python structure — extends the SDK quarantine from F-088 to formalize the adapter/driver/raw-SDK three-layer boundary from GOLDEN_VISION_V2.
- **Integration Points:** `sdk_adapter/` directory, depends on F-088
- **Recommended Pattern:** Organize `sdk_adapter/` internal structure to separate type translation (adapter), session lifecycle (driver), and raw SDK access (quarantined via `_imports.py`).

### F-069: Remove complete_fn Dead Code
- **Architectural Impact:** Python cleanup — removes a dead code path from `provider.py`. Less code = less confusion for AI agents.
- **Integration Points:** `provider.py`
- **Recommended Pattern:** Verify zero references via LSP `findReferences`, then delete. Run tests.

### F-070: Cleanup Deferred Imports
- **Architectural Impact:** Python cleanup — replaces deferred/lazy imports with standard top-of-file imports where safe. Makes dependency graph explicit.
- **Integration Points:** Multiple files with `import inside function` patterns
- **Recommended Pattern:** Move imports to module level. If circular import exists, document why and keep deferred.

### F-089: Align SessionConfig Shape with Contract (absorbs F-071)
- **Architectural Impact:** Python types — aligns `sdk_adapter/types.py` `SessionConfig` with `contracts/sdk-boundary.md`. Removes unused fields (F-071's scope), adds missing fields.
- **Integration Points:** `sdk_adapter/types.py`, all `SessionConfig` constructors, session factory
- **Recommended Pattern:** Compare `SessionConfig` fields with contract spec. Add/remove fields. Update all construction sites. Use dataclass defaults for new fields.

### F-087: Strengthen complete Parameter Type
- **Architectural Impact:** Python types — makes `complete()` parameter type more specific than `Any`/`**kwargs`.
- **Integration Points:** `provider.py` `complete()` signature
- **Recommended Pattern:** Use `ChatRequest` with proper type hints. Align with kernel protocol.

---

## Phase 8: Provider Decomposition

**Architectural Goal:** Extract `provider.py` from a monolith into the Three-Medium Architecture's target: `provider.py` (~120 lines thin orchestrator) + `completion.py` (~150 lines LLM call lifecycle) + `response.py` (response extraction). This is the most architecturally significant change in the entire project.

**Entry Conditions:**
- ALL features that modify `provider.py` are complete: F-049, F-052, F-054, F-059, F-065, F-067, F-069, F-070, F-072, F-078, F-082, F-084, F-085, F-087
- Phase 7 structural refactoring complete (SDK quarantine, SessionConfig, dead code removed)
- All tests pass
- Test quality is high (F-067 complete)

**Exit Conditions:**
- `provider.py` is ≤200 lines — thin orchestrator only
- `completion.py` extracted — LLM call lifecycle
- `response.py` extracted (if applicable) — response extraction logic
- All extracted modules have clear contracts (imports flow down, no cycles)
- All tests pass with identical behavior

**Key Invariants to Preserve:**
- INV-1: Deny hook installed (must survive decomposition)
- INV-2: Sessions ephemeral (session lifecycle in completion.py, not split across modules)
- INV-3: No SDK type crosses boundary
- INV-4: All tests pass — behavioral equivalence is MANDATORY
- INV-7: Error translation uses kernel types

**Architectural Risks:**
- **Risk (CRITICAL):** Decomposition introduces behavioral regression — the most dangerous failure mode per GOLDEN_VISION_V2 Risk R1 → **Mitigation:** Extract one function at a time. Run full test suite after each extraction. If any test fails, revert the extraction and investigate.
- **Risk:** Circular imports between `provider.py` and extracted modules → **Mitigation:** Follow dependency rule from GOLDEN_VISION_V2: imports flow DOWN only. `provider.py` imports `completion.py`, never the reverse. Shared types live in `_types.py`.
- **Risk:** 13 features touched `provider.py` — the file has diverged significantly from its original structure → **Mitigation:** Read the current file state completely before planning extractions. Do not assume pre-Phase-1 structure.

**Feature Implementation Notes:**

### F-065: Provider Decomposition
- **Architectural Impact:** Python structure — this IS the Three-Medium Architecture's Python layer reaching its target form. The ~1800-line monolith becomes ~120-line orchestrator + focused modules.
- **Integration Points:** `provider.py` (source), `completion.py` (new), potentially `response.py` (new), `_types.py` (shared types), all test files that import from `provider.py`
- **Recommended Pattern:**
  1. Identify extraction boundaries: completion lifecycle = one module, response extraction = one module
  2. Extract `_complete_with_sdk()` and related helpers → `completion.py`
  3. Extract `extract_response_content()` and related → `response.py` (if substantial enough)
  4. Keep `provider.py` as thin orchestrator: `complete()` delegates to `completion.complete()`
  5. Move shared types to `_types.py` if not already there
  6. Update `__init__.py` exports
  7. Run full test suite after each extraction step

---

## Phase 9: Test & Packaging Polish

**Architectural Goal:** Finalize the codebase for release. Harden architecture tests, fix test warnings, ensure PyPI readiness, and add ephemeral session invariant tests. In Three-Medium terms, this is the final quality gate ensuring all three mediums are consistent, tested, and publishable.

**Entry Conditions:**
- Phase 8 complete — provider decomposed, all modules at target size
- All tests pass
- No features remain that modify production code structure

**Exit Conditions:**
- Architecture tests are hardened (F-062)
- Async mock warnings fixed (F-076)
- Enum type fix in test_contract_events (F-083)
- Ephemeral session invariant tests exist (F-091)
- PyPI publishing readiness verified (F-064)
- Bundle.md metadata complete (F-080)
- All tests pass
- `ruff check`, `ruff format --check`, and `pyright` all clean

**Key Invariants to Preserve:**
- ALL invariants (INV-1 through INV-7) — this is the final verification phase

**Architectural Risks:**
- **Risk:** F-062 architecture test hardening adds tests that fail on the current codebase → **Mitigation:** Only add tests that verify invariants the codebase already satisfies. New invariants require their own feature specs.
- **Risk:** F-064 PyPI readiness reveals missing metadata or packaging issues → **Mitigation:** Test with `python -m build` + `twine check` before declaring complete.

**Feature Implementation Notes:**

### F-062: Architecture Test Hardening
- **Architectural Impact:** Test tier — strengthens the CI gates that enforce the Three-Medium Architecture invariants (no SDK imports outside boundary, no hardcoded policy in Python, etc.)
- **Integration Points:** `tests/test_architecture*.py` or similar
- **Recommended Pattern:** Add tests for: (1) SDK import quarantine, (2) config file schema validation, (3) contract file path validity, (4) module size limits. Each test cites the architectural invariant it enforces.

### F-076: Fix Async Mock Warning
- **Architectural Impact:** Test quality — eliminates `DeprecationWarning` about `asyncio.iscoroutinefunction` on mocks.
- **Integration Points:** Test files using `AsyncMock`
- **Recommended Pattern:** Use the correct mock pattern for the Python version. May require `unittest.mock.AsyncMock` configuration.

### F-083: Fix test_contract_events Enum Type
- **Architectural Impact:** Test correctness — fixes enum misuse in contract event tests.
- **Integration Points:** `tests/test_contract_events.py`
- **Recommended Pattern:** Use proper enum comparison instead of string comparison.

### F-091: Ephemeral Session Invariant Tests
- **Architectural Impact:** Test tier — contract compliance tests for `contracts/deny-destroy.md` ephemeral session requirement. Verifies INV-2 programmatically.
- **Integration Points:** New test file, `contracts/deny-destroy.md`
- **Recommended Pattern:** Test that: (1) sessions are created per-request, (2) sessions are destroyed after use, (3) no session state carries between requests, (4) deny hook is present on every session.

### F-064: PyPI Publishing Readiness
- **Architectural Impact:** Packaging — ensures the package can be published to PyPI. Verifies `pyproject.toml` metadata, entry points, classifiers, README, license.
- **Integration Points:** `pyproject.toml`, `README.md`, `bundle.md`
- **Recommended Pattern:** Run `python -m build`, `twine check dist/*`. Verify entry point `[project.entry-points."amplifier.modules"]` exists per Errata E7 in GOLDEN_VISION_V2.

### F-080: Add Missing PyPI Metadata
- **Architectural Impact:** Packaging — adds required metadata fields to `pyproject.toml` or `bundle.md`.
- **Integration Points:** `pyproject.toml`, `bundle.md`
- **Recommended Pattern:** Add: `description`, `license`, `classifiers`, `urls`, `keywords`. Follow ecosystem conventions from Errata E6.

---

## Cross-Phase Dependency Graph

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6 ──→ Phase 7 ──→ Phase 8 ──→ Phase 9
 (clean)    (sovereignty) (config)   (critical)  (harden)    (errors)    (retry)     (refactor)  (decompose) (polish)

Key dependency chains:
  F-074 (Ph2) ──→ F-060, F-061, F-066, F-068 (Ph5-6) [config must be in wheel first]
  F-088 (Ph7) ──→ F-063 (Ph7) [quarantine before structure]
  F-066 (Ph5) ──→ F-061 (Ph5) [fix algorithm before adding mappings]
  F-072 (Ph3) ──→ F-073 (Ph3) [implementation before tests]
  ALL provider.py features ──→ F-065 (Ph8) [decompose LAST]
```

## Three-Medium Compliance Checklist

For each feature, verify:

| Check | Question |
|-------|----------|
| **Python = Mechanism** | Does the Python code implement translation logic only? No hardcoded thresholds, no embedded mappings? |
| **YAML = Policy** | Are all tunable values in `config/*.yaml`? Do they have sensible defaults? |
| **Markdown = Contract** | Does a contract in `contracts/` specify the MUST requirements? Does a test verify it? |
| **Deny+Destroy** | Is the sovereignty invariant preserved? Could this feature accidentally make it configurable? |
| **SDK Boundary** | Do SDK types stay inside `sdk_adapter/`? Does the adapter translate, not wrap? |
| **Kernel Types** | Are all error types from `amplifier_core.llm_errors`? No custom `Copilot*Error` classes? |

---

**END OF ARCHITECTURAL NOTES**

*Document Authority: Zen Architect analysis of AMPLIFIER-DIRECTIVE-2026-03-15.md + GOLDEN_VISION_V2.md + STATE.yaml*
