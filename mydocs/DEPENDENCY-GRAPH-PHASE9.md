# Phase 9: Dependency Graph & Implementation Ordering

**Generated:** 2026-03-15
**Authority:** AMPLIFIER-DIRECTIVE-2026-03-15.md
**Scope:** 43 features (F-049 to F-091), 41 implementable (2 DROP, 1 SUPERSEDED)

---

# PART 1: Feature Dependency Graph

## Phase 1: Zero-Risk Cleanups + Sovereignty

### F-049: Fix Architecture Test Paths

**Depends On:** None
**Blocks:** F-074, F-062 (all subsequent phases assume correct paths)
**Files Modified:** `tests/test_contract_deny_destroy.py`, `tests/test_sdk_client.py`, `contracts/provider-protocol.md`, `contracts/error-hierarchy.md`, `contracts/event-vocabulary.md`, `contracts/sdk-boundary.md`, `contracts/streaming-contract.md`, `contracts/deny-destroy.md`
**Conflict Risk:** Low — touches test files and markdown contracts only

### F-050: Mandatory Deny Hook Installation

**Depends On:** None
**Blocks:** F-052, F-072, F-085 (sovereignty invariant must be established before SDK integration)
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py`, `tests/test_contract_deny_destroy.py`
**Conflict Risk:** Medium — touches client.py (6 features total touch this file)

### F-077: Delete Tombstone Test Files

**Depends On:** None
**Blocks:** None
**Files Modified:** `tests/test_placeholder.py` (deletion), possibly other tombstone files
**Conflict Risk:** Low — file deletions only

### F-079: Add py.typed Marker

**Depends On:** None
**Blocks:** F-064 (PyPI readiness depends on typing metadata)
**Files Modified:** `amplifier_module_provider_github_copilot/py.typed` (new file)
**Conflict Risk:** Low — new file creation only

### F-084: Remove Redundant Path Import

**Depends On:** None
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (line 233, redundant `from pathlib import Path`)
**Conflict Risk:** Low — single import removal, but provider.py is high-traffic (13 features)

---

## Phase 2: Config Foundation

### F-074: Config Not in Wheel

**Depends On:** F-049 (paths must be correct first)
**Blocks:** F-060, F-061, F-066, F-068, F-053, F-078 (ALL config-dependent features)
**Files Modified:** `pyproject.toml` (hatch build config), `amplifier_module_provider_github_copilot/provider.py` (config path resolution), `amplifier_module_provider_github_copilot/streaming.py` (config path resolution), `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (config path resolution), possibly `config/__init__.py`
**Conflict Risk:** High — changes config loading paths in 3 source files + build config

### F-081: Fix context_extraction in Client Error Loading

**Depends On:** F-049 (correct paths)
**Blocks:** F-053 (unified config loading depends on correct parsing)
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (lines 86-98, `_load_error_config_once()`)
**Conflict Risk:** Medium — touches client.py parsing logic

### F-078: Add context_window to Fallback Config

**Depends On:** F-074 (config must be in wheel first)
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (`_default_provider_config()`, `get_info()`), `config/models.yaml`
**Conflict Risk:** Medium — touches provider.py defaults section

---

## Phase 3: P0 Critical Path

### F-072: Real SDK Path Error Translation

**Depends On:** F-050 (deny hook must be in place), F-074 (config loading correct)
**Blocks:** F-073 (tests for this feature)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (lines 477-495, real SDK path — add try/except + translate_sdk_error)
**Conflict Risk:** High — modifies the critical real SDK code path in provider.py

### F-073: Real SDK Path Error Test

**Depends On:** F-072 (implementation must exist to test)
**Blocks:** None
**Files Modified:** `tests/` (new test file or additions to `test_provider.py`)
**Conflict Risk:** Low — test files only

### F-052: Real SDK Streaming Pipeline

**Depends On:** F-050 (deny hook), F-072 (error translation in SDK path)
**Blocks:** F-065 (decomposition needs all provider.py changes landed)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (lines 477-498, replace send_and_wait with streaming on()+queue pattern), `amplifier_module_provider_github_copilot/streaming.py` (possibly new StreamEvent types)
**Conflict Risk:** High — major rewrite of real SDK path in provider.py

### F-051: Defensive Event Config Loading

**Depends On:** F-074 (config in wheel)
**Blocks:** F-068 (event classification validation)
**Files Modified:** `amplifier_module_provider_github_copilot/streaming.py` (`load_event_config()` — add try/except around YAML parse)
**Conflict Risk:** Medium — touches streaming.py (3 features total)

---

## Phase 4: Robustness Hardening

### F-085: Add Timeout Enforcement (Real SDK Path)

**Depends On:** F-072 (error translation wrapping must exist), F-052 (streaming pipeline)
**Blocks:** F-065 (provider.py must be stable before decomposition)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (add asyncio.wait_for or timeout around SDK calls)
**Conflict Risk:** High — modifies real SDK path in provider.py (same region as F-052, F-072)

### F-082: Wire provider.close() to client.close()

**Depends On:** None (standalone fix)
**Blocks:** F-065 (provider.py changes must land first)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (lines 517-523, replace pass with `await self._client.close()`)
**Conflict Risk:** Low — isolated method, no overlap with other provider.py regions

### F-053: Unify Error Config Loading

**Depends On:** F-074 (config in wheel), F-081 (context_extraction fix)
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (`_load_error_config_once()`), `amplifier_module_provider_github_copilot/error_translation.py` (`load_error_config()`), `amplifier_module_provider_github_copilot/provider.py` (config loading in `complete()`)
**Conflict Risk:** High — touches 3 source files, all config-loading code paths

### F-054: Response Extraction Recursion Guard

**Depends On:** None
**Blocks:** F-065 (provider.py changes)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (`extract_response_content()`, lines 121-157 — add depth limit)
**Conflict Risk:** Medium — isolated function but in provider.py

### F-055: Streaming Accumulator Completion Guard

**Depends On:** None
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/streaming.py` (`StreamingAccumulator.add()` — guard against events after completion)
**Conflict Risk:** Low — isolated method in streaming.py

### F-056: SDK Client Failed Start Cleanup

**Depends On:** None
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (session() method — cleanup `_owned_client` on start failure)
**Conflict Risk:** Medium — touches client.py session initialization

---

## Phase 5: Error & Integration

### F-066: Error Translation Safety

**Depends On:** F-074 (config loading)
**Blocks:** F-061 (algorithm must be safe before adding mappings)
**Files Modified:** `amplifier_module_provider_github_copilot/error_translation.py` (`_matches_mapping()` — safety for regex/pattern matching)
**Conflict Risk:** Medium — touches error_translation.py (3 features total)

### F-061: Error Config Missing Mappings

**Depends On:** F-066 (matching algorithm must be safe first), F-074 (config in wheel)
**Blocks:** None
**Files Modified:** `config/errors.yaml` (add missing mappings), `amplifier_module_provider_github_copilot/error_translation.py` (possibly)
**Conflict Risk:** Medium — config file + error_translation.py

### F-068: Event Classification Validation

**Depends On:** F-051 (event config loading must be defensive), F-074 (config in wheel)
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/streaming.py` (validate event classifications for overlap)
**Conflict Risk:** Medium — streaming.py

### F-059: ChatRequest Multi-Turn Context

**Depends On:** None (standalone enhancement)
**Blocks:** F-065 (provider.py changes)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (complete() method — enhance ChatRequest→prompt conversion to preserve conversation history)
**Conflict Risk:** High — modifies complete() in provider.py

### F-086: Handle Session Disconnect Failures

**Depends On:** None
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (session() finally block — enhance disconnect error handling)
**Conflict Risk:** Low — isolated finally block in client.py

---

## Phase 6: Retry System

### F-075: Retry YAML Dead Config

**Depends On:** None
**Blocks:** F-060 (must delete dead config before creating real one)
**Files Modified:** `config/retry.yaml` (deletion or cleanup)
**Conflict Risk:** Low — config file change only

### F-060: Config-Driven Retry

**Depends On:** F-074 (config in wheel), F-075 (dead config cleared)
**Blocks:** None
**Files Modified:** `config/retry.yaml` (new content or new file), `amplifier_module_provider_github_copilot/provider.py` or new retry module
**Conflict Risk:** Medium — may touch provider.py for retry wiring

### F-090: Behavioral Tests for Behaviors Contract

**Depends On:** None (test-only)
**Blocks:** None
**Files Modified:** `tests/` (new test file)
**Conflict Risk:** Low — test files only

---

## Phase 7: Structural Refactoring

### F-067: Test Quality Improvements

**Depends On:** None
**Blocks:** F-065 (test quality must improve before decomposition makes tests harder to change)
**Files Modified:** Various `tests/test_*.py` files
**Conflict Risk:** Low — test files only, but broad scope

### F-088: Create _imports.py SDK Quarantine

**Depends On:** None
**Blocks:** F-063 (SDK boundary structure extends quarantine)
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/_imports.py` (new file), `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (move SDK imports to _imports.py)
**Conflict Risk:** Medium — restructures imports in client.py

### F-063: SDK Boundary Structure

**Depends On:** F-088 (_imports.py must exist)
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py`, `amplifier_module_provider_github_copilot/sdk_adapter/__init__.py`
**Conflict Risk:** Medium — extends SDK adapter structure

### F-069: Remove complete_fn Dead Code

**Depends On:** None
**Blocks:** F-065 (dead code must be removed before decomposition)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (`_complete_fn`, `_complete_internal()`, `complete()` function, `complete_and_collect()` function)
**Conflict Risk:** High — removes significant code from provider.py

### F-070: Cleanup Deferred Imports

**Depends On:** None
**Blocks:** F-065 (imports must be clean before decomposition)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (move deferred imports to top-level)
**Conflict Risk:** Medium — touches import section of provider.py

### F-089: Align SessionConfig Shape with Contract (absorbs F-071)

**Depends On:** None
**Blocks:** None
**Files Modified:** `amplifier_module_provider_github_copilot/sdk_adapter/types.py` (SessionConfig fields), `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (session() method — update SessionConfig usage)
**Conflict Risk:** Medium — touches types.py and client.py

### F-087: Strengthen complete Parameter Type

**Depends On:** None
**Blocks:** F-065 (provider.py type changes before decomposition)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (complete() signature — `request: Any` → stronger type)
**Conflict Risk:** Medium — touches complete() signature in provider.py

---

## Phase 8: Provider Decomposition

### F-065: Provider Decomposition

**Depends On:** ALL provider.py features: F-052, F-054, F-059, F-067, F-069, F-070, F-072, F-078, F-082, F-084, F-085, F-087
**Blocks:** None (terminal feature for provider.py)
**Files Modified:** `amplifier_module_provider_github_copilot/provider.py` (split into provider.py + completion.py + response.py), new files `completion.py`, `response.py`
**Conflict Risk:** Critical — full restructure of the largest source file

---

## Phase 9: Test & Packaging Polish

### F-062: Architecture Test Hardening

**Depends On:** F-049 (paths correct), F-065 (final structure known)
**Blocks:** None
**Files Modified:** `tests/test_contract_deny_destroy.py`, `tests/test_sdk_client.py`, `tests/test_sdk_boundary_contract.py`
**Conflict Risk:** Low — test files only

### F-076: Fix Async Mock Warning

**Depends On:** None
**Blocks:** None
**Files Modified:** Various `tests/test_*.py` files (replace deprecated `asyncio.iscoroutinefunction` patterns)
**Conflict Risk:** Low — test files only

### F-083: Fix Test Contract Events Enum Type

**Depends On:** None
**Blocks:** None
**Files Modified:** `tests/test_contract_events.py`
**Conflict Risk:** Low — single test file

### F-091: Ephemeral Session Invariant Tests

**Depends On:** None (but best after F-050, F-082)
**Blocks:** None
**Files Modified:** `tests/` (new test file)
**Conflict Risk:** Low — test files only

### F-064: PyPI Publishing Readiness

**Depends On:** F-079 (py.typed marker), F-074 (config in wheel), F-080 (metadata)
**Blocks:** None (terminal feature)
**Files Modified:** `pyproject.toml`, `bundle.md`, possibly `README.md`
**Conflict Risk:** Low — metadata files only

### F-080: Add Missing PyPI Metadata

**Depends On:** None
**Blocks:** F-064 (metadata must be complete for PyPI)
**Files Modified:** `pyproject.toml`, `bundle.md`
**Conflict Risk:** Low — metadata files only

---

## DROPPED / SUPERSEDED Features (No Implementation)

### F-057: Provider Close Cleanup — **DROPPED** (superseded by F-082)
### F-058: SDK Request Timeout Enforcement — **DROPPED** (merged into F-085)
### F-071: Remove Unused SessionConfig Fields — **SUPERSEDED** (merged into F-089)

---

# PART 2: Safe Implementation Order by Phase

## Phase 1: Zero-Risk Cleanups + Sovereignty (~1 iteration)

**Pre-Phase Action:** Delete orphan `src/` directory

1. **F-049** — Foundation: fixes all paths, unblocks everything
2. **F-079** — Independent: creates new file only (py.typed)
3. **F-077** — Independent: deletes tombstone files only
4. **F-084** — Independent: single import removal in provider.py
5. **F-050** — Last: touches client.py, establishes sovereignty invariant

**Parallel Opportunities:**
- [F-049, F-079, F-077] can be implemented in parallel (no shared files)
- F-084 is independent but touches provider.py (safe to parallel with F-079/F-077)

**Serial Requirements:**
- F-049 MUST complete before Phase 2 (paths must be correct)
- F-050 SHOULD be last in Phase 1 (sovereignty before SDK work)

---

## Phase 2: Config Foundation (~1-2 iterations)

1. **F-074** — CRITICAL FIRST: moves config into wheel, changes all config path resolution
2. **F-081** — After F-074: fixes context_extraction parsing in client.py
3. **F-078** — After F-074: adds context_window to fallback config in provider.py

**Parallel Opportunities:**
- [F-081, F-078] can be implemented in parallel after F-074 (different files: client.py vs provider.py)

**Serial Requirements:**
- F-074 MUST complete before F-081 and F-078
- F-074 MUST complete before ALL features in Phases 3-9 that touch config

---

## Phase 3: P0 Critical Path (~2 iterations)

1. **F-072** — FIRST: adds try/except + error translation to real SDK path in provider.py
2. **F-073** — After F-072: tests for the error translation
3. **F-051** — Independent: defensive event config loading in streaming.py
4. **F-052** — LAST: replaces real SDK path with streaming pipeline (depends on F-072 error handling being in place)

**Parallel Opportunities:**
- [F-073, F-051] can run in parallel after F-072 (different files)

**Serial Requirements:**
- F-072 MUST complete before F-073 (implementation before tests)
- F-072 MUST complete before F-052 (error translation must wrap the new streaming code)

---

## Phase 4: Robustness Hardening (~2 iterations)

1. **F-082** — First: wire provider.close() (isolated method, no dependency)
2. **F-055** — Independent: accumulator guard in streaming.py
3. **F-054** — Independent: recursion guard in provider.py (extract_response_content)
4. **F-056** — Independent: client start cleanup in client.py
5. **F-053** — After F-081: unify config loading across 3 files
6. **F-085** — LAST: timeout enforcement on real SDK path (must follow F-052 streaming)

**Parallel Opportunities:**
- [F-082, F-055, F-054, F-056] can all run in parallel (touch different functions/files)

**Serial Requirements:**
- F-053 requires F-081 complete (context_extraction fix)
- F-085 requires F-052 complete (streaming pipeline must exist)
- F-085 MUST be after F-082 (close wiring provides the cleanup path timeout needs)

---

## Phase 5: Error & Integration (~1-2 iterations)

1. **F-066** — FIRST: fix error matching safety in error_translation.py
2. **F-061** — After F-066: add missing error mappings
3. **F-068** — After F-051: event classification validation
4. **F-059** — Independent: multi-turn context in provider.py complete()
5. **F-086** — Independent: disconnect failure handling in client.py

**Parallel Opportunities:**
- [F-068, F-059, F-086] can all run in parallel (different files/functions)
- F-061 can parallel with [F-068, F-059, F-086] but MUST follow F-066

**Serial Requirements:**
- F-066 MUST complete before F-061 (safe matching before new mappings)

---

## Phase 6: Retry System (~1 iteration)

1. **F-075** — FIRST: delete dead retry.yaml
2. **F-060** — After F-075: implement config-driven retry
3. **F-090** — Independent: behavioral tests (test-only)

**Parallel Opportunities:**
- F-090 can run in parallel with F-075 + F-060 (test-only, no source overlap)

**Serial Requirements:**
- F-075 MUST complete before F-060 (clear dead config before creating real one)

---

## Phase 7: Structural Refactoring (~2 iterations)

1. **F-088** — FIRST: create _imports.py SDK quarantine
2. **F-067** — Independent: test quality improvements (broad test changes)
3. **F-063** — After F-088: extend SDK boundary structure
4. **F-069** — Independent: remove complete_fn dead code from provider.py
5. **F-070** — After F-069: cleanup deferred imports in provider.py
6. **F-089** — Independent: align SessionConfig shape (types.py + client.py)
7. **F-087** — Independent: strengthen complete() parameter type in provider.py

**Parallel Opportunities:**
- [F-088, F-067, F-069, F-089] can all start in parallel
- F-087 can parallel with F-089 (different files: provider.py vs types.py)

**Serial Requirements:**
- F-088 MUST complete before F-063 (quarantine file must exist)
- F-069 SHOULD complete before F-070 (remove dead code before reorganizing imports)
- ALL Phase 7 MUST complete before Phase 8

---

## Phase 8: Provider Decomposition (~1-2 iterations)

1. **F-065** — ONLY feature. Extracts completion.py and response.py from provider.py.

**Serial Requirements:**
- ALL of these must be complete: F-052, F-054, F-059, F-067, F-069, F-070, F-072, F-078, F-082, F-084, F-085, F-087

---

## Phase 9: Test & Packaging Polish (~1-2 iterations)

1. **F-080** — First: add PyPI metadata to pyproject.toml
2. **F-083** — Independent: fix enum type in test file
3. **F-076** — Independent: fix async mock warnings across tests
4. **F-091** — Independent: ephemeral session invariant tests
5. **F-062** — After F-065: architecture test hardening (needs final structure)
6. **F-064** — LAST: PyPI readiness (needs F-079, F-074, F-080 all done)

**Parallel Opportunities:**
- [F-080, F-083, F-076, F-091] can all run in parallel
- F-062 can parallel with F-064 (different concerns)

**Serial Requirements:**
- F-064 MUST be last (aggregates all packaging prerequisites)
- F-062 SHOULD follow F-065 (test hardening against final architecture)

---

# PART 3: File Conflict Matrix

| File | Features Touching It | Risk Level | Notes |
|------|---------------------|------------|-------|
| **provider.py** | F-052, F-054, F-059, F-065, F-069, F-070, F-072, F-074, F-078, F-082, F-084, F-085, F-087 | **Critical (13)** | Strict serial order within phases. F-065 MUST be last. |
| **sdk_adapter/client.py** | F-050, F-053, F-056, F-074, F-081, F-086, F-088, F-089 | **High (8)** | Multiple regions: init, session(), close(), config loading. Parallel OK if touching different regions. |
| **streaming.py** | F-051, F-052, F-055, F-068 | **Medium (4)** | F-052 may add new types. F-051/F-055/F-068 touch different functions. |
| **error_translation.py** | F-053, F-061, F-066 | **Medium (3)** | F-066 before F-061 (safety before mappings). F-053 touches loader. |
| **sdk_adapter/types.py** | F-089 | **Low (1)** | Only F-089 (F-071 superseded). |
| **sdk_adapter/__init__.py** | F-063, F-088 | **Low (2)** | Export changes. F-088 before F-063. |
| **sdk_adapter/_imports.py** | F-088 | **Low (1)** | New file creation. |
| **__init__.py** | None | **None** | No pending features touch this. |
| **tool_parsing.py** | None | **None** | No pending features touch this. |
| **config/errors.yaml** | F-061 | **Low (1)** | Single feature adds mappings. |
| **config/events.yaml** | F-068 | **Low (1)** | Validation only, may not modify. |
| **config/models.yaml** | F-078 | **Low (1)** | Add context_window default. |
| **config/retry.yaml** | F-060, F-075 | **Low (2)** | F-075 deletes, F-060 creates/replaces. |
| **pyproject.toml** | F-064, F-074, F-080 | **Medium (3)** | Build config + metadata. Different sections. |
| **bundle.md** | F-064, F-080 | **Low (2)** | Metadata only. |
| **tests/test_contract_deny_destroy.py** | F-049, F-050, F-062 | **Medium (3)** | Path fix → deny hook test → hardening. Serial order. |
| **tests/test_sdk_client.py** | F-049, F-062 | **Low (2)** | Path fix → hardening. |
| **tests/test_contract_events.py** | F-083 | **Low (1)** | Single enum fix. |
| **tests/ (various)** | F-067, F-076 | **Low (2)** | Broad test improvements. May overlap files but different concerns. |
| **tests/ (new files)** | F-073, F-090, F-091 | **Low (3)** | New test files, no conflicts. |

### Critical provider.py Region Map

| Region (Lines) | Features | Conflict Pattern |
|----------------|----------|-----------------|
| Imports (22-51) | F-070, F-084 | F-084 first (remove), F-070 later (reorganize) |
| Config loading (76-118) | F-074, F-078 | F-074 first (paths), F-078 after (defaults) |
| extract_response_content (121-157) | F-054 | Isolated — safe anytime |
| complete() method (423-498) | F-052, F-059, F-072, F-085, F-087 | **HIGHEST RISK.** Strict order: F-072 → F-052 → F-085 → F-059 → F-087 |
| _complete_internal (500-515) | F-069 | Removal. Must be after all test changes. |
| close() (517-523) | F-082 | Isolated — safe anytime |
| complete_and_collect (295-325) | F-069 | Removal candidate. |

---

# PART 4: SDK Compatibility Verification

### F-052: Real SDK Streaming Pipeline

**SDK Method Used:** `session.send()` (non-blocking) + `session.on(handler)` (event subscription)
**Verified in Reference:** Yes — `copilot-sdk/python/e2e/test_streaming_fidelity.py:14-42`
**SDK Event Types:** `SessionEventType.ASSISTANT_MESSAGE_DELTA`, `ASSISTANT_MESSAGE`, `SESSION_IDLE`, `SESSION_ERROR`
**Compatibility Risk:** Low — pattern verified against SDK e2e tests
**Note:** Replaces current `send_and_wait()` with `send()` + `on()` + `asyncio.Queue` pattern

### F-072: Real SDK Path Error Translation

**SDK Method Used:** `sdk_session.send_and_wait()` (existing) — wraps with try/except
**Verified in Reference:** Yes — `amplifier_module_provider_github_copilot/provider.py:481-495` (current code, no try/except)
**Compatibility Risk:** Low — adds error handling around existing SDK call

### F-085: Add Timeout Enforcement

**SDK Method Used:** `asyncio.wait_for()` wrapping `sdk_session.send_and_wait()` or streaming queue
**Verified in Reference:** Yes — SDK's `send_and_wait()` has built-in timeout (default 60s) per `copilot-sdk/python/copilot/session.py`
**Compatibility Risk:** Medium — must coordinate with SDK's own timeout. Our timeout should be outer guard (e.g., 120s) around SDK's inner timeout (60s).

### F-050: Mandatory Deny Hook Installation

**SDK Method Used:** `session.register_pre_tool_use_hook()`, `on_permission_request` handler
**Verified in Reference:** Yes — `amplifier_module_provider_github_copilot/sdk_adapter/client.py:240-243` (already registered, F-050 makes it mandatory/asserted)
**Compatibility Risk:** Low — strengthening existing behavior

### F-059: ChatRequest Multi-Turn Context

**SDK Method Used:** `send_and_wait({"prompt": ...})` or `send({"prompt": ...})`
**Verified in Reference:** Yes — SDK accepts `MessageOptions` with `prompt` field
**Compatibility Risk:** Medium — need to verify if SDK supports conversation history natively or if we must concatenate into single prompt
**Note:** SDK `send()` accepts `MessageOptions` which has `prompt` field. Multi-turn may require session-level context or prompt engineering.

### F-082: Wire provider.close() to client.close()

**SDK Method Used:** `CopilotClient.stop()` (via `CopilotClientWrapper.close()`)
**Verified in Reference:** Yes — `amplifier_module_provider_github_copilot/sdk_adapter/client.py:258-268`
**Compatibility Risk:** Low — client.close() already implemented and tested

### F-086: Handle Session Disconnect Failures

**SDK Method Used:** `session.disconnect()` (existing)
**Verified in Reference:** Yes — `amplifier_module_provider_github_copilot/sdk_adapter/client.py:251-256` (already has try/except, F-086 enhances)
**Compatibility Risk:** Low — enhancing existing error handling

### F-056: SDK Client Failed Start Cleanup

**SDK Method Used:** `CopilotClient.start()` + `CopilotClient.stop()` for cleanup
**Verified in Reference:** Yes — `amplifier_module_provider_github_copilot/sdk_adapter/client.py:199-201` (start without cleanup on failure)
**Compatibility Risk:** Low — adding finally block around existing start()

### F-088: Create _imports.py SDK Quarantine

**SDK Method Used:** All SDK imports (`from copilot import ...`)
**Verified in Reference:** Yes — `amplifier_module_provider_github_copilot/sdk_adapter/client.py` lines 57, 188
**Compatibility Risk:** Low — import reorganization only, no behavioral change

---

# PART 5: Critical Path Summary

```
Phase 0: Delete src/ + apply spec amendments
    │
Phase 1: F-049 ──→ [F-079, F-077, F-084] (parallel) ──→ F-050
    │
Phase 2: F-074 ──→ [F-081, F-078] (parallel)
    │
Phase 3: F-072 ──→ [F-073, F-051] (parallel) ──→ F-052
    │
Phase 4: [F-082, F-055, F-054, F-056] (parallel) ──→ F-053 ──→ F-085
    │
Phase 5: F-066 ──→ F-061 ─┐
         [F-068, F-059, F-086] (parallel) ─┘
    │
Phase 6: F-075 ──→ F-060 ─┐
         F-090 (parallel) ─┘
    │
Phase 7: [F-088, F-067, F-069, F-089] (parallel) ──→ [F-063, F-070, F-087] ──→ all done
    │
Phase 8: F-065 (REQUIRES all above)
    │
Phase 9: [F-080, F-083, F-076, F-091] (parallel) ──→ F-062 ──→ F-064 (LAST)
```

**Total Estimated Iterations:** 12-17
**Critical Path Length:** F-049 → F-074 → F-072 → F-052 → F-085 → F-069 → F-065 → F-064

---

**END OF DOCUMENT**
