# AMPLIFIER DIRECTIVE: Phase 9 Pre-Implementation Constitution

**Authority:** Principal Engineering Review
**Date:** 2026-03-15
**Version:** 1.0 (Definitive)
**Purpose:** Complete, self-contained directive for autonomous dev-machine execution

---

## DIRECTIVE SUMMARY

This document is the **SINGLE SOURCE OF TRUTH** for Phase 9 implementation. Amplifier MUST read this document in its entirety before executing any feature. All decisions are final unless Amplifier convenes an expert panel to contest with code evidence.

| Metric | Value |
|--------|-------|
| **Total Features (F-001 to F-091)** | 91 feature numbers |
| **Spec Files in specs/features/** | 90 files |
| **Completed Features (STATE.yaml)** | 48 |
| **Pending Features (Phase 9)** | 43 (F-049 to F-091) |
| **Features to DROP** | 2 (F-057, F-058) |
| **Features BLOCKED** | 1 (F-052 - needs SDK verification) |
| **Net Implementable Features** | 40 |
| **Implementation Phases** | 9 |

---

# PART 1: COMPLETED FEATURES REGISTRY (F-001 to F-048)

These features are DONE. Do not reimplement. Reference only for context.

## 1.1 Completed Feature List (48 features)

| Feature | Status | Notes |
|---------|--------|-------|
| F-001-sdk-adapter-skeleton | ✅ DONE | Skeleton structure |
| F-002-error-translation | ✅ DONE | Error mapping foundation |
| F-003-session-factory | ✅ DONE | Session creation |
| F-004-tool-parsing | ✅ DONE | Tool extraction |
| F-005-event-translation | ✅ DONE | SDK → Domain events |
| F-006-streaming-handler | ✅ DONE | Streaming pipeline |
| F-007-completion-lifecycle | ✅ DONE | Completion flow |
| F-008-provider-orchestrator | ✅ DONE | Provider structure |
| F-009-integration-verification | ✅ DONE | Integration tests |
| F-010-sdk-client-wrapper | ✅ DONE | SDK wrapper |
| F-011-loop-controller | ✅ DONE | Agent loop |
| F-017-technical-debt-cleanup | ✅ DONE | Debt cleanup |
| F-018-aggressive-simplification | ✅ DONE | Simplification |
| F-019-critical-security-fixes | ✅ DONE | Security fixes |
| F-020-protocol-compliance | ✅ DONE | Protocol compliance |
| F-021-bug-fixes | ✅ DONE | Bug fixes |
| F-022-foundation-integration | ✅ DONE | Foundation integration |
| F-023-test-coverage | ✅ DONE | Test coverage |
| F-024-code-quality | ✅ DONE | Code quality |
| F-025-ci-pipeline | ✅ DONE | CI pipeline |
| F-026-contract-compliance-tests | ✅ DONE | Contract tests |
| F-027-real-sdk-integration | ✅ DONE | Real SDK |
| F-028-entry-point | ✅ DONE | Entry point |
| F-029-documentation-update | ✅ DONE | Documentation |
| F-030-changelog | ✅ DONE | Changelog |
| F-031-system-notification-event | ✅ DONE | System notification |
| F-032-permission-handler-tests | ✅ DONE | Permission tests |
| F-033-permission-handler-fix | ✅ DONE | Permission fix |
| F-034-sdk-version-tests | ✅ DONE | SDK version tests |
| F-035-error-type-expansion | ✅ DONE | Error types |
| F-036-error-context-enhancement | ✅ DONE | Error context |
| F-037-observability-improvements | ✅ DONE | Observability |
| F-038-kernel-type-migration | ✅ DONE | Kernel types |
| F-039-sdk-client-wiring | ✅ DONE | SDK wiring |
| F-040-sdk-api-fix | ✅ DONE | SDK API fix |
| F-043-sdk-response-fix | ✅ DONE | Response fix |
| F-044-system-prompt-replace-mode | ✅ DONE | System prompt |
| F-045-disable-sdk-builtin-tools | ✅ DONE | Disable tools |
| F-046-sdk-integration-testing-architecture | ✅ DONE | Test architecture |
| F-047-testing-course-correction | ✅ DONE | Test correction |
| F-048-config-extraction | ✅ DONE | Config extraction |

### 1.2 Missing Spec Files (No Action Required)

| Feature Number | Status | Explanation |
|----------------|--------|-------------|
| F-012 to F-016 | Completed but no current spec file | Legacy — work done |
| F-039, F-040 | Completed in STATE.yaml | Specs may have been deleted post-completion |
| F-041, F-042 | TRULY MISSING | Never existed — number gap |

**ACTION:** Create tombstone files `F-041-RESERVED.md` and `F-042-RESERVED.md` to document the gap.

### 1.3 Duplicate Spec Numbers (Completed Features)

These spec files have DUPLICATE numbers but are already completed:

| Number | File 1 | File 2 | Resolution |
|--------|--------|--------|------------|
| F-002 | F-002-error-translation.md | F-002-provider-protocol-contract.md | Both completed — no action |
| F-003 | F-003-error-hierarchy-contract.md | F-003-session-factory.md | Both completed — no action |
| F-004 | F-004-session-factory.md | F-004-tool-parsing.md | Both completed — no action |
| F-005 | F-005-basic-completion.md | F-005-event-translation.md | Both completed — no action |

**NOTE:** Future features MUST use unique numbers. No action needed for completed work.

---

# PART 2: CRITICAL PRE-IMPLEMENTATION ACTIONS

Before executing ANY Phase 9 feature, these MUST be done:

## 2.1 ACTION: Delete Orphan `src/` Directory

**Evidence:**
```
Directory: D:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot

Contents:
- __pycache__/
- sdk_adapter/__pycache__/

NO .py files. Only orphan bytecode cache from path migration.
```

**Impact:** Architecture tests scan this directory but find zero files, passing vacuously.

**Command:**
```powershell
Remove-Item -Recurse -Force "d:\next-get-provider-github-copilot\src"
```

**Execute:** BEFORE F-049

---

## 2.2 ACTION: Fix Contract Module Reference Paths

**Evidence (grep search results):**
```
contracts/deny-destroy.md:5     → modules/provider-core/session_factory.py (WRONG)
contracts/event-vocabulary.md:5 → src/amplifier_module_provider_github_copilot/streaming.py
contracts/error-hierarchy.md:5  → src/amplifier_module_provider_github_copilot/error_translation.py
contracts/provider-protocol.md:5 → src/amplifier_module_provider_github_copilot/provider.py
contracts/sdk-boundary.md:5     → src/amplifier_module_provider_github_copilot/sdk_adapter/
contracts/streaming-contract.md:5 → src/amplifier_module_provider_github_copilot/streaming.py
```

**Actual paths (no `src/` prefix):**
```
amplifier_module_provider_github_copilot/streaming.py
amplifier_module_provider_github_copilot/error_translation.py
amplifier_module_provider_github_copilot/provider.py
amplifier_module_provider_github_copilot/sdk_adapter/
amplifier_module_provider_github_copilot/sdk_adapter/client.py
```

**Fix Required (6 files):**

### contracts/provider-protocol.md line 5:
```markdown
# BEFORE:
- **Module Reference:** src/amplifier_module_provider_github_copilot/provider.py

# AFTER:
- **Module Reference:** amplifier_module_provider_github_copilot/provider.py
```

### contracts/error-hierarchy.md line 5:
```markdown
# BEFORE:
- **Module Reference:** src/amplifier_module_provider_github_copilot/error_translation.py

# AFTER:
- **Module Reference:** amplifier_module_provider_github_copilot/error_translation.py
```

### contracts/event-vocabulary.md line 5:
```markdown
# BEFORE:
- **Module Reference:** src/amplifier_module_provider_github_copilot/streaming.py

# AFTER:
- **Module Reference:** amplifier_module_provider_github_copilot/streaming.py
```

### contracts/sdk-boundary.md line 5:
```markdown
# BEFORE:
- **Module Reference:** src/amplifier_module_provider_github_copilot/sdk_adapter/

# AFTER:
- **Module Reference:** amplifier_module_provider_github_copilot/sdk_adapter/
```

### contracts/streaming-contract.md line 5:
```markdown
# BEFORE:
- **Module Reference:** src/amplifier_module_provider_github_copilot/streaming.py

# AFTER:
- **Module Reference:** amplifier_module_provider_github_copilot/streaming.py
```

### contracts/deny-destroy.md line 5:
```markdown
# BEFORE:
- **Module Reference:** modules/provider-core/session_factory.py

# AFTER:
- **Module Reference:** amplifier_module_provider_github_copilot/sdk_adapter/client.py
```

**Execute:** As part of F-049 OR as pre-Phase 1 action

---

## 2.3 ACTION: Clear STATE.yaml Blockers

**Current blockers (10 entries):** All are documentation amendment requests that cannot be addressed via operator sessions.

**Resolution:** Remove blockers and add this directive as context.

**STATE.yaml update:**
```yaml
blockers:
  - "2026-03-15: All prior principal review blockers resolved via AMPLIFIER-DIRECTIVE-2026-03-15.md. See mydocs/deep-review/AMPLIFIER-DIRECTIVE-2026-03-15.md for complete resolution."
```

---

# PART 3: SDK CAPABILITIES CONTRACT

This section documents the ACTUAL Copilot SDK Python API capabilities, verified against `copilot-sdk/python/copilot/session.py`.

## 3.1 Session API Methods

| Method | Signature | Returns | Behavior |
|--------|-----------|---------|----------|
| `send(options)` | `async def send(self, options: MessageOptions) -> str` | Message ID (string) | Non-blocking. Returns immediately. Events delivered via `on()` handlers. |
| `send_and_wait(options, timeout)` | `async def send_and_wait(self, options: MessageOptions, timeout: float | None = None) -> SessionEvent | None` | Final SessionEvent or None | **BLOCKING.** Waits for `session.idle` event. Default timeout: 60 seconds. |
| `on(handler)` | `def on(self, handler: Callable[[SessionEvent], None]) -> Callable[[], None]` | Unsubscribe function | Event subscription. Handler receives all session events. |
| `disconnect()` | `async def disconnect(self) -> None` | None | Closes session. |

## 3.2 CRITICAL: No AsyncIterator API

**F-052 assumes this pattern:**
```python
async for sdk_event in session.send_message(request.prompt, request.tools):
    domain_event = translate_event(sdk_event, event_config)
```

**REALITY:** The SDK has NO `send_message()` method that returns an AsyncIterator.

**Evidence (copilot-sdk/python/copilot/session.py lines 117-207):**
- `send()` returns `str` (message ID)
- `send_and_wait()` returns `SessionEvent | None` (blocking)
- `on()` provides callback-based event subscription

**Why test path works:**
```python
# provider.py line 271 (test path)
async for sdk_event in session.send_message(request.prompt, request.tools):
```
This works because tests MOCK `session.send_message` — the real SDK doesn't have it.

## 3.3 Streaming Pattern (If Needed)

To receive streaming events from SDK:
```python
# Correct pattern using send() + on()
def handler(event: SessionEvent) -> None:
    # Process each event as it arrives
    domain_event = translate_event(event, event_config)
    accumulator.add(domain_event)

unsubscribe = session.on(handler)
try:
    await session.send({"prompt": prompt})
    # Wait for completion signal
    await wait_for_idle()
finally:
    unsubscribe()
```

**DECISION:** F-052 must be BLOCKED until this pattern is verified with live SDK testing.

---

# PART 4: PENDING FEATURES REGISTRY (F-049 to F-091)

## 4.1 Feature Status Matrix

| Feature | Priority | Status | Action | Phase |
|---------|----------|--------|--------|-------|
| F-049-fix-architecture-test-paths | P0 | ready | IMPLEMENT + EXPAND | 1 |
| F-050-mandatory-deny-hook-installation | P1 | ready | IMPLEMENT | 3 |
| F-051-defensive-event-config-loading | P0 | ready | IMPLEMENT | 3 |
| F-052-real-sdk-streaming-pipeline | P0 | **BLOCKED** | DEFER — SDK verification needed | — |
| F-053-unify-error-config-loading | P1 | ready | IMPLEMENT | 4 |
| F-054-response-extraction-recursion-guard | P1 | ready | IMPLEMENT | 4 |
| F-055-streaming-accumulator-completion-guard | P1 | ready | IMPLEMENT | 4 |
| F-056-sdk-client-failed-start-cleanup | P1 | ready | IMPLEMENT | 4 |
| F-057-provider-close-cleanup | P1 | **DROP** | Superseded by F-082 | — |
| F-058-sdk-request-timeout-enforcement | P1 | **DROP** | Merged into F-085 | — |
| F-059-chatrequest-multi-turn-context | P2 | ready | IMPLEMENT | 5 |
| F-060-config-driven-retry | P2 | ready | IMPLEMENT | 6 |
| F-061-error-config-missing-mappings | P2 | ready | IMPLEMENT | 5 |
| F-062-architecture-test-hardening | P2 | ready | IMPLEMENT | 9 |
| F-063-sdk-boundary-structure | P2 | ready | IMPLEMENT after F-088 | 7 |
| F-064-pypi-publishing-readiness | P2 | ready | IMPLEMENT | 9 |
| F-065-provider-decomposition | P2 | ready | IMPLEMENT LAST | 8 |
| F-066-error-translation-safety | P2 | ready | IMPLEMENT | 5 |
| F-067-test-quality-improvements | P3 | ready | IMPLEMENT | 9 |
| F-068-event-classification-validation | P2 | ready | IMPLEMENT | 5 |
| F-069-remove-complete-fn-dead-code | P2 | ready | IMPLEMENT | 7 |
| F-070-cleanup-deferred-imports | P2 | ready | IMPLEMENT | 7 |
| F-071-remove-unused-sessionconfig-fields | P2 | **SUPERSEDED** | Merged into F-089 | — |
| F-072-real-sdk-path-error-translation | P0 | **AMEND** | IMPLEMENT + type fix | 3 |
| F-073-real-sdk-path-error-test | P1 | **AMEND** | IMPLEMENT + type fix | 3 |
| F-074-config-not-in-wheel | P0 | ready | IMPLEMENT | 2 |
| F-075-retry-yaml-dead-config | P2 | ready | IMPLEMENT | 6 |
| F-076-fix-async-mock-warning | P3 | ready | IMPLEMENT | 9 |
| F-077-delete-tombstone-test-files | P3 | ready | IMPLEMENT | 1 |
| F-078-add-context-window-to-fallback-config | P2 | ready | IMPLEMENT | 2 |
| F-079-add-py-typed-marker | P2 | ready | IMPLEMENT | 1 |
| F-080-add-missing-pypi-metadata | P2 | ready | IMPLEMENT | 9 |
| F-081-fix-context-extraction-in-client-error-loading | P0 | ready | IMPLEMENT | 2 |
| F-082-wire-provider-close-to-client-close | P1 | ready | IMPLEMENT | 4 |
| F-083-fix-test-contract-events-enum-type | P2 | ready | IMPLEMENT | 9 |
| F-084-remove-redundant-path-import | P3 | ready | IMPLEMENT | 1 |
| F-085-add-timeout-enforcement-real-sdk-path | P1 | ready | IMPLEMENT (includes F-058) | 4 |
| F-086-handle-session-disconnect-failures | P2 | ready | IMPLEMENT | 5 |
| F-087-strengthen-complete-parameter-type | P2 | ready | IMPLEMENT | 7 |
| F-088-create-imports-py-sdk-quarantine | P2 | ready | IMPLEMENT first of pair | 7 |
| F-089-align-sessionconfig-shape-with-contract | P2 | ready | IMPLEMENT (includes F-071) | 7 |
| F-090-behavioral-tests-for-behaviors-contract | P1 | ready | IMPLEMENT | 6 |
| F-091-ephemeral-session-invariant-tests | P1 | ready | IMPLEMENT | 9 |

**Summary:**
- IMPLEMENT: 37 features
- DROP: 2 (F-057, F-058)
- AMEND: 2 (F-072, F-073)
- BLOCKED: 1 (F-052)
- SUPERSEDED: 1 (F-071 → F-089)

---

# PART 5: SPEC AMENDMENTS (Complete Text)

## 5.1 F-072 Amendment: Type Name Correction

**File:** `specs/features/F-072-real-sdk-path-error-translation.md`

**Change 1 (TDD Anchor section, line ~46):**
```markdown
# BEFORE:
- Red: `sdk_session.send_and_wait()` raises `RuntimeError` → currently bubbles raw → after fix, translated to `LLMProviderError`

# AFTER:
- Red: `sdk_session.send_and_wait()` raises `RuntimeError` → currently bubbles raw → after fix, translated to `ProviderUnavailableError`
```

**Change 2 (Implementation Approach code block, line ~34):**
```markdown
# BEFORE:
except Exception as e:
    from .error_translation import load_error_config, translate_sdk_error
    error_config = load_error_config(Path(__file__).parent.parent / "config" / "errors.yaml")
    raise translate_sdk_error(e, error_config, provider="github-copilot", model=model) from e

# AFTER (no change needed — translate_sdk_error already returns ProviderUnavailableError as default)
# The issue is only in the TDD Anchor documentation
```

**Rationale:** `LLMProviderError` does not exist in `amplifier_core.llm_errors`. The actual default fallback type is `ProviderUnavailableError` per `config/errors.yaml` and `error_translation.py` KERNEL_ERROR_MAP.

---

## 5.2 F-073 Amendment: Type Name Correction

**File:** `specs/features/F-073-real-sdk-path-error-test.md`

**Change (Test cases section, line ~31):**
```markdown
# BEFORE:
- Generic `RuntimeError` → `LLMProviderError` (fallback)

# AFTER:
- Generic `RuntimeError` → `ProviderUnavailableError` (fallback)
```

---

## 5.3 F-052 Amendment: Mark BLOCKED

**File:** `specs/features/F-052-real-sdk-streaming-pipeline.md`

**Add new section after Status header:**
```markdown
**Status:** blocked
**Priority:** P0
**Source:** deep-review/integration-specialist.md
**Defect ID:** N/A (structural correctness failure)
**Blocked By:** SDK capability verification required

## BLOCKING ISSUE

This spec assumes the SDK supports streaming event iteration via `async for`. 

**VERIFIED SDK REALITY (copilot-sdk/python/copilot/session.py):**
- `send(options)` → returns message ID only (non-blocking)
- `send_and_wait(options, timeout)` → returns final SessionEvent (blocking)
- `on(handler)` → event subscription via callback
- **NO `send_message()` AsyncIterator method exists**

**Resolution Options:**
1. **OPTION A:** Redesign spec to use `send()` + `on()` event callback pattern
2. **OPTION B:** Defer feature and implement F-072 first (makes blocking path safe)
3. **OPTION C:** Verify if newer SDK versions added async iterator API

**RECOMMENDED:** OPTION B — Implement F-072 first. Defer F-052 until SDK streaming capabilities are verified with live testing.

## Original Problem Statement
[... rest of spec unchanged ...]
```

---

## 5.4 F-049 Amendment: Expand Scope

**File:** `specs/features/F-049-fix-architecture-test-paths.md`

**Replace "Files to Modify" section with:**
```markdown
## Files to Modify (Expanded)

### Tests (Original Scope)
- `tests/test_contract_deny_destroy.py` (line 81): Change `Path("src/amplifier_module_provider_github_copilot")` → `Path("amplifier_module_provider_github_copilot")`
- `tests/test_sdk_client.py` (line 191): Same path change

### Contracts (Added Scope)
- `contracts/provider-protocol.md` (line 5): `src/amplifier_module...` → `amplifier_module...`
- `contracts/error-hierarchy.md` (line 5): `src/amplifier_module...` → `amplifier_module...`
- `contracts/event-vocabulary.md` (line 5): `src/amplifier_module...` → `amplifier_module...`
- `contracts/sdk-boundary.md` (line 5): `src/amplifier_module...` → `amplifier_module...`
- `contracts/streaming-contract.md` (line 5): `src/amplifier_module...` → `amplifier_module...`
- `contracts/deny-destroy.md` (line 5): `modules/provider-core/session_factory.py` → `amplifier_module_provider_github_copilot/sdk_adapter/client.py`

### Pre-Implementation Action
- DELETE `src/` directory (contains only orphan `__pycache__/` — no source files)
```

---

## 5.5 F-071 Mark Superseded

**File:** `specs/features/F-071-remove-unused-sessionconfig-fields.md`

**Add at top of file:**
```markdown
**Status:** superseded
**Superseded By:** F-089-align-sessionconfig-shape-with-contract
**Reason:** F-089 aligns SessionConfig to contract while also addressing unused fields. Implementing both separately risks conflict.
```

---

# PART 6: STATE.yaml UPDATE INSTRUCTIONS

Apply these changes to STATE.yaml:

## 6.1 Remove Old Blockers

Delete all existing blocker entries and replace with:
```yaml
blockers:
  - "2026-03-15: Principal review complete. See mydocs/deep-review/AMPLIFIER-DIRECTIVE-2026-03-15.md for all decisions."
```

## 6.2 Update Feature Statuses

```yaml
features:
  F-052-real-sdk-streaming-pipeline:
    status: blocked
    priority: P0
    source: deep-review/integration-specialist.md
    blocked_by: "SDK verification required - see AMPLIFIER-DIRECTIVE Part 5.3"
  
  F-057-provider-close-cleanup:
    status: superseded
    priority: P1
    superseded_by: F-082-wire-provider-close-to-client-close
  
  F-058-sdk-request-timeout-enforcement:
    status: superseded
    priority: P1
    superseded_by: F-085-add-timeout-enforcement-real-sdk-path
  
  F-071-remove-unused-sessionconfig-fields:
    status: superseded
    priority: P2
    superseded_by: F-089-align-sessionconfig-shape-with-contract
  
  F-072-real-sdk-path-error-translation:
    status: ready
    priority: P0
    source: deep-review/code-navigator-v2.md
    amendment: "Type name corrected: LLMProviderError → ProviderUnavailableError"
  
  F-073-real-sdk-path-error-test:
    status: ready
    priority: P1
    source: deep-review/code-navigator-v2.md
    amendment: "Type name corrected: LLMProviderError → ProviderUnavailableError"
```

## 6.3 Update next_action

```yaml
next_action: "Execute Phase 1: Delete src/, fix paths in contracts/tests, implement F-049, F-077, F-079, F-084"
```

---

# PART 7: IMPLEMENTATION PHASES (Complete Order)

## Phase 0: Pre-Implementation (Manual)

| Action | Command/File | Status |
|--------|--------------|--------|
| Delete src/ directory | `Remove-Item -Recurse -Force "src"` | Required |
| Apply spec amendments | F-072, F-073, F-052, F-049, F-071 | Required |
| Update STATE.yaml | See Part 6 | Required |

---

## Phase 1: Zero-Risk Cleanups (~1 iteration)

| Feature | Priority | Description |
|---------|----------|-------------|
| **F-049** | P0 | Fix architecture test paths + contract paths |
| F-077 | P3 | Delete tombstone test files |
| F-079 | P2 | Add py.typed marker |
| F-084 | P3 | Remove redundant Path import |

**Dependencies:** None
**Exit Criteria:** All tests pass, contracts have correct paths

---

## Phase 2: Config Foundation (~1-2 iterations)

| Feature | Priority | Description |
|---------|----------|-------------|
| **F-074** | P0 | Move config/ into wheel package |
| **F-081** | P0 | Fix context_extraction parsing bug |
| F-078 | P2 | Add context_window to fallback config |

**Dependencies:** F-049 complete
**Exit Criteria:** Config loads correctly from installed wheel

**CRITICAL:** F-074 MUST complete before ANY config-related feature (F-060, F-061, F-066, F-068)

---

## Phase 3: P0 Critical Path (~2 iterations)

| Feature | Priority | Description | Notes |
|---------|----------|-------------|-------|
| **F-072** | P0 | Error translation in complete() | **IMPLEMENT FIRST** |
| F-073 | P1 | Tests for F-072 | After F-072 |
| F-051 | P0 | Event config safety | — |
| F-050 | P1 | Deny hook enforcement | — |

**F-052 is BLOCKED — do not implement**

**EVIDENCE: provider.py lines 479-495 has NO try/except**
```python
else:
    # Real SDK path: use client wrapper
    model = internal_request.model or "gpt-4o"
    async with self._client.session(model=model) as sdk_session:
        sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
        # NO TRY/EXCEPT HERE — raw SDK exceptions escape
```

---

## Phase 4: Robustness Hardening (~2 iterations)

| Feature | Priority | Description |
|---------|----------|-------------|
| **F-085** | P1 | Timeout enforcement (absorbs F-058) |
| **F-082** | P1 | Wire provider.close() to client.close() |
| F-053 | P1 | Unify config loaders |
| F-054 | P1 | Response extraction recursion guard |
| F-055 | P1 | Accumulator completion guard |
| F-056 | P1 | SDK client failed start cleanup |

**EVIDENCE: provider.py lines 517-523 close() is no-op**
```python
async def close(self) -> None:
    """Clean up provider resources."""
    # Currently no resources to clean up
    pass  # ← NO-OP
```

**While client.py lines 258-268 has working close():**
```python
async def close(self) -> None:
    """Clean up owned client resources."""
    if self._owned_client is not None:
        await self._owned_client.stop()
        self._owned_client = None
```

---

## Phase 5: Error & Integration (~1-2 iterations)

| Feature | Priority | Description | Order |
|---------|----------|-------------|-------|
| F-066 | P2 | Error matching safety | First |
| F-061 | P2 | Add error mappings | After F-066 |
| F-068 | P2 | Event overlap validation | — |
| F-059 | P2 | Multi-turn context | — |
| F-086 | P2 | Disconnect tracking | — |

---

## Phase 6: Retry System (~1 iteration)

| Feature | Priority | Description | Order |
|---------|----------|-------------|-------|
| F-075 | P2 | Delete dead retry.yaml | First |
| F-060 | P2 | Implement config-driven retry | After F-075 |
| F-090 | P1 | Behavioral tests | — |

---

## Phase 7: Structural Refactoring (~2 iterations)

| Feature | Priority | Description | Order |
|---------|----------|-------------|-------|
| **F-088** | P2 | Create _imports.py SDK quarantine | First |
| F-063 | P2 | Extend SDK quarantine | After F-088 |
| F-069 | P2 | Remove complete_fn dead code | — |
| F-070 | P2 | Cleanup deferred imports | — |
| **F-089** | P2 | Align SessionConfig (absorbs F-071) | — |
| F-087 | P2 | Strengthen complete parameter type | — |

---

## Phase 8: Provider Decomposition (~1-2 iterations)

| Feature | Priority | Description |
|---------|----------|-------------|
| **F-065** | P2 | Extract completion.py/response.py |

**CRITICAL:** F-065 MUST be LAST provider.py change. All 13 features touching provider.py must land first:
- F-052 (blocked), F-054, F-059, F-065, F-067, F-069, F-070, F-072, F-078, F-082, F-084, F-085, F-087

---

## Phase 9: Test & Packaging Polish (~1-2 iterations)

| Feature | Priority | Description |
|---------|----------|-------------|
| F-062 | P2 | Architecture test hardening |
| F-067 | P3 | Test quality improvements |
| F-076 | P3 | Async mock warning fix |
| F-083 | P3 | Enum type fix |
| F-091 | P1 | Ephemeral session tests |
| F-064 | P2 | PyPI readiness |
| F-080 | P2 | Bundle.md metadata |

---

# PART 8: FILE CONFLICT RISK MAP

## 8.1 Critical Risk Files

| File | Feature Count | Features |
|------|---------------|----------|
| **provider.py** | 13 | F-052(blocked), F-054, F-059, F-065, F-067, F-069, F-070, F-072, F-078, F-082, F-084, F-085, F-087 |
| **sdk_adapter/client.py** | 6 | F-050, F-053, F-056, F-081, F-086, F-088 |
| **sdk_adapter/types.py** | 2 | F-071(superseded), F-089 |
| **config/** | 5 | F-074, F-075, F-078, F-060, F-061 |
| **streaming.py** | 3 | F-051, F-055, F-068 |
| **error_translation.py** | 3 | F-053, F-061, F-066 |

## 8.2 Ordering Constraints

1. **F-074 before all config features** — config location changes
2. **F-088 before F-063** — F-088 creates _imports.py
3. **F-066 before F-061** — F-066 fixes algorithm, F-061 adds mappings
4. **F-065 LAST for provider.py** — decomposition after all changes
5. **F-072 before F-073** — implementation before tests

---

# PART 9: EVIDENCE ARCHIVE

## 9.1 Real SDK Path Has No Error Translation

**File:** `amplifier_module_provider_github_copilot/provider.py`
**Lines:** 479-495

```python
else:
    # Real SDK path: use client wrapper
    # F-040: Fixed SDK API - use send_and_wait(), not send_message()
    model = internal_request.model or "gpt-4o"
    async with self._client.session(model=model) as sdk_session:
        # SDK uses send_and_wait() for blocking call
        sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})

        # Extract response content and convert to domain event
        # F-043: Use extract_response_content() to handle Data objects
        if sdk_response is not None:
            content = extract_response_content(sdk_response)

            # Create CONTENT_DELTA event with correct DomainEvent signature
            text_event = DomainEvent(
                type=DomainEventType.CONTENT_DELTA,
                data={"text": content},
            )
            accumulator.add(text_event)
```

**Finding:** No try/except. No translate_sdk_error(). Raw SDK exceptions escape.

---

## 9.2 provider.close() Is No-Op

**File:** `amplifier_module_provider_github_copilot/provider.py`
**Lines:** 517-523

```python
async def close(self) -> None:
    """Clean up provider resources.

    Feature: F-020 AC-1
    """
    # Currently no resources to clean up
    pass
```

**Finding:** Does nothing. Resources leaked.

---

## 9.3 client.close() EXISTS and Works

**File:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py`
**Lines:** 258-268

```python
async def close(self) -> None:
    """Clean up owned client resources. Safe to call multiple times."""
    if self._owned_client is not None:
        try:
            logger.info("[CLIENT] Stopping owned Copilot client...")
            await self._owned_client.stop()
            logger.info("[CLIENT] Copilot client stopped")
        except Exception as e:
            logger.warning(f"[CLIENT] Error stopping client: {e}")
        finally:
            self._owned_client = None
```

**Finding:** Proper cleanup exists. Just never called from provider.

---

## 9.4 _load_error_config_once() Missing context_extraction

**File:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py`
**Lines:** 86-98

```python
mappings.append(
    ErrorMapping(
        sdk_patterns=mapping_data.get("sdk_patterns", []),
        string_patterns=mapping_data.get("string_patterns", []),
        kernel_error=mapping_data.get("kernel_error", "ProviderUnavailableError"),
        retryable=mapping_data.get("retryable", True),
        extract_retry_after=mapping_data.get("extract_retry_after", False),
        # MISSING: context_extraction=mapping_data.get("context_extraction", [])
    )
)
```

**Finding:** F-036 functionality (context extraction) is silently dropped.

---

## 9.5 SDK Session API (No AsyncIterator)

**File:** `copilot-sdk/python/copilot/session.py`
**Lines:** 117-207

**Methods documented:**
- `send(options)` → returns `str` (message ID)
- `send_and_wait(options, timeout)` → returns `SessionEvent | None`
- `on(handler)` → callback subscription

**Finding:** No `send_message()` AsyncIterator exists. F-052's implementation approach is invalid.

---

## 9.6 Kernel Error Types (No LLMProviderError)

**File:** `amplifier_module_provider_github_copilot/error_translation.py`
**Lines:** 44-56

```python
from amplifier_core.llm_errors import (
    AbortError,
    AccessDeniedError,
    AuthenticationError,
    ConfigurationError,
    ContentFilterError,
    ContextLengthError,
    InvalidRequestError,
    InvalidToolCallError,
    LLMError,
    LLMTimeoutError,
    NetworkError,
    NotFoundError,
    ProviderUnavailableError,  # ← This is the fallback type
    QuotaExceededError,
    RateLimitError,
    StreamError,
)
```

**Finding:** `LLMProviderError` does not exist. F-072/F-073 reference a non-existent type.

---

# PART 10: VERIFICATION CHECKLIST

Before the dev-machine proceeds, verify:

| Check | Status | Evidence |
|-------|--------|----------|
| src/ directory deleted | ☐ | `Test-Path "src"` returns False |
| Contract paths fixed | ☐ | grep shows no `src/amplifier` in contracts/ |
| F-072 spec amended | ☐ | Spec says `ProviderUnavailableError` |
| F-073 spec amended | ☐ | Spec says `ProviderUnavailableError` |
| F-052 marked blocked | ☐ | STATE.yaml shows `status: blocked` |
| F-049 scope expanded | ☐ | Spec includes contracts in scope |
| F-071 marked superseded | ☐ | STATE.yaml shows `status: superseded` |
| F-057 marked superseded | ☐ | STATE.yaml shows `status: superseded` |
| F-058 marked superseded | ☐ | STATE.yaml shows `status: superseded` |
| STATE.yaml blockers cleared | ☐ | Only directive reference remains |

---

# PART 11: FINAL DIRECTIVE

## 11.1 GO/NO-GO Decision

**GO** — with the following conditions:

1. ☐ Part 2 actions completed (delete src/, fix contracts)
2. ☐ Part 5 amendments applied to spec files
3. ☐ Part 6 STATE.yaml updates applied
4. ☐ Part 10 verification checklist passes

## 11.2 Expert Panel Override

If Amplifier disagrees with ANY decision in this directive:

1. **Convene expert panel** — minimum 3 agents with different specializations
2. **Cite code evidence** — line numbers and file paths required
3. **Document counter-argument** — in CONTEXT-TRANSFER.md
4. **Human approval required** — for any decision that overrides this directive

## 11.3 Scope Boundaries

**Amplifier MAY:**
- Implement features in the order specified
- Make minor adjustments to implementation details
- Add defensive code beyond spec requirements

**Amplifier MUST NOT:**
- Implement F-052 until SDK verification complete
- Implement F-057, F-058, F-071 (superseded)
- Skip F-074 before other config features
- Implement F-065 before all other provider.py features

---

**END OF DIRECTIVE**

*Document Authority: Principal Engineering Review*
*Machine: laptop | Date: 2026-03-15*
*This document supersedes all prior review documents in mydocs/deep-review/*
