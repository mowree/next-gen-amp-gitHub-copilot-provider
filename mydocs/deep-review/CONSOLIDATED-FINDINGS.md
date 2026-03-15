# CONSOLIDATED FINDINGS: Pre-Implementation Quality Gate

**Date:** 2026-03-15  
**Status:** REVISED AFTER EXPERT PANEL VALIDATION  
**Purpose:** Holistic validation of 43 features (F-049 to F-091) before autonomous dev-machine execution  
**Revision:** Applied corrections from zen-architect and amplifier-expert validation pass  

---

## Executive Summary

A panel of four expert agents conducted independent holistic reviews of the 43-feature backlog:

| Expert | Focus Area | Key Finding |
|--------|------------|-------------|
| **zen-architect** | Architectural Alignment | 8 duplicates, 4 conflicts identified |
| **amplifier-expert** | Ecosystem Alignment | CRITICAL: Dual codebase divergence |
| **integration-specialist** | Dependencies & Ordering | 9-phase implementation plan, 4 duplicate pairs |
| **core-expert** | Kernel Contract Compliance | 37/43 compliant, 3 critical violations |

### Overall Assessment

| Metric | Value |
|--------|-------|
| **Total Features** | 43 (F-049 to F-091) |
| **Duplicates/Superseded** | 4-8 (depending on resolution) |
| **Net Distinct Features** | ~35-39 |
| **Critical Violations** | 3 (must fix before execution) |
| **Implementation Phases** | 9 |

---

## SECTION 1: CRITICAL BLOCKERS (Must Resolve Before Execution)

### BLOCKER 1: Path Drift in Tests and Specs (amplifier-expert — REVISED)

**Corrected Assessment:** This is path drift, NOT two separate codebases.

The project has ONE active implementation:
- `amplifier_module_provider_github_copilot/` — Active development target (contains all code)

The issue is that tests and specs contain **stale references** to a non-existent `src/...` path:

**Evidence:**
- `tests/test_contract_deny_destroy.py` line 81 scans `src/...` which **does not exist**
- Architecture fitness tests pass **vacuously** because they scan non-existent paths
- Some specs and contracts reference `src/...` path inconsistently

**Resolution Required:**
1. **UPDATE** all test paths to scan `amplifier_module_provider_github_copilot/` (F-049)
2. **UPDATE** all specs/contracts with stale `src/...` references
3. **NO directory deletion needed** — the `src/` path doesn't exist as a directory

**Affected Features:** F-049 fixes this directly. F-092 creation is NOT needed.

---

### BLOCKER 2: Kernel Type Violations (core-expert)

Three features reference non-existent or incorrect kernel types:

| Feature | References | Should Be |
|---------|------------|-----------|
| **F-072** | `LLMProviderError` | `ProviderUnavailableError` (from `amplifier_core.llm_errors`) |
| **F-073** | `LLMProviderError` | `ProviderUnavailableError` |
| **F-052** | `TextContent` dataclass | `TextBlock` (Pydantic model from `amplifier_core.types`) |

**Resolution Required:**
1. **AMEND F-072 spec** to use `ProviderUnavailableError` 
2. **AMEND F-073 spec** to use `ProviderUnavailableError`
3. **AMEND F-052 spec** to use `TextBlock` from kernel types, not custom dataclass

---

### BLOCKER 3: F-052 SDK Compatibility Unverified (integration-specialist)

F-052 assumes the GitHub Copilot SDK supports streaming event iteration (not just `send_and_wait()`).

**Risk:** If the SDK only supports `send_and_wait()`, F-052's entire approach is invalid.

**Resolution Required:**
1. **VERIFY** SDK capabilities in `reference-only/amplifier-module-provider-github-copilot/`
2. If streaming not supported: **REDESIGN F-052** or **DEFER** it
3. Document SDK capabilities in a new contract file

---

## SECTION 2: DUPLICATES (Must Merge or Drop)

### Confirmed Duplicates (4 pairs)

| Feature A | Feature B | Nature | Resolution |
|-----------|-----------|--------|------------|
| **F-057** | **F-082** | F-082 explicitly supersedes F-057 (same fix for real SDK path) | **DROP F-057** |
| **F-058** | **F-085** | Both add timeout to `send_and_wait()` at provider.py:481-495 | **MERGE into F-085** (more specific) |
| **F-063** | **F-088** | Both create `_imports.py` for SDK quarantine | **F-088 first**, F-063 becomes incremental |
| **F-064** | **F-074** | Both move `config/` into package | **F-074 first** (P0), F-064 becomes metadata-only |

### Additional Potential Duplicates (zen-architect)

| Feature A | Feature B | Nature | Assessment |
|-----------|-----------|--------|------------|
| F-051 | F-068 | Both validate event config | **KEEP BOTH** — F-051 is safety, F-068 is overlap detection |
| F-053 | F-081 | Both address config loading | **KEEP BOTH** — F-081 fixes bug, F-053 unifies loaders |
| F-066 | F-061 | Both modify error mappings | **KEEP BOTH** — F-066 fixes algorithm, F-061 adds mappings (F-066 first) |
| F-071 | F-089 | Both modify SessionConfig | **IMPLEMENT TOGETHER** as single unit |

**Net Effect:** 43 features → **39 distinct work items** (4 dropped/merged)

---

## SECTION 3: CONFLICTS (Must Resolve Order or Intent)

### CONFLICT 1: F-052 ↔ F-072 (Tight Coupling)

Both features modify the same code block (`provider.py:479-498`):
- **F-052:** Replaces `send_and_wait()` with streaming (changes call pattern)
- **F-072:** Wraps SDK call with try/except (error translation)

**Resolution:** 
- Implement **F-052 first** (establishes new call pattern)
- Then **F-072** wraps the streaming pattern
- **OR** implement together in single iteration by same implementer

---

### CONFLICT 2: F-071 ↔ F-089 (SessionConfig Fields)

Both features modify `SessionConfig`:
- **F-071:** Removes `system_prompt`/`max_tokens` fields
- **F-089:** Renames `system_prompt` → `system_message`

If F-071 removes the field, F-089's rename is moot.

**Resolution:**
- **Decision required:** Remove or rename?
- **IMPLEMENT TOGETHER** as single coordinated change
- Recommend: Rename (F-089) + remove `max_tokens` (partial F-071)

---

### CONFLICT 3: F-075 ↔ F-060 (Retry Config)

- **F-075:** Deletes `retry.yaml` (dead config)
- **F-060:** Implements config-driven retry using `retry.yaml`

**Resolution:**
- **If implementing retry (F-060):** Skip F-075, F-060 creates proper config
- **If deferring retry:** Do F-075 first (delete dead config)
- **Recommendation:** F-075 first (clean state), F-060 creates fresh config when needed

---

### CONFLICT 4: Three-Medium Architecture Violations (zen-architect)

Several features create Python code that should be config or documentation:

| Feature | Violation | Should Be |
|---------|-----------|-----------|
| F-060 | "Implement retry logic in Python" | Retry behavior should be YAML policy + minimal Python mechanism |
| F-066 | "Safety checks in error matching" | This IS mechanism (keep in Python) |
| F-068 | "Validate event overlap" | Validation is mechanism (keep in Python) |

**Resolution:** 
- F-060 needs spec amendment to emphasize YAML-driven with minimal Python
- F-066, F-068 are correctly mechanism — no change

---

## SECTION 4: GAPS (Missing Features)

### GAP 1: ~~No Feature for Deleting `src/` Directory~~ (RESOLVED)

**Corrected:** F-049 already addresses the path drift issue. No F-092 needed — the `src/` path doesn't exist as a directory; it's just stale references in tests/specs that F-049 fixes.

---

### GAP 2: SDK Capability Contract Missing

No contract documents what the GitHub Copilot SDK actually supports (streaming? hooks? error types?).

**Recommendation:** Create `contracts/sdk-capabilities.md` documenting verified SDK behaviors.

---

### GAP 3: No E2E Integration Test Feature

All test features are unit/contract level. No feature for live SDK integration test.

**Assessment:** Acceptable — live tests require credentials and are out of scope for autonomous execution.

---

## SECTION 5: IMPLEMENTATION ORDER (9 Phases)

Based on integration-specialist's dependency analysis:

### Phase 1 — Zero-Risk Cleanups (4 features, ~1 iteration)
| Feature | Priority | Description |
|---------|----------|-------------|
| **F-049** | P0 | Fix architecture test paths (enables all subsequent test features) |
| F-077 | P3 | Delete tombstone files |
| F-079 | P2 | Add py.typed marker |
| F-084 | P3 | Remove duplicate import |

---

### Phase 2 — Config Foundation (3 features, ~1-2 iterations)
| Feature | Priority | Description |
|---------|----------|-------------|
| **F-074** | P0 | Move config into wheel (ALL config features depend on this) |
| **F-081** | P0 | Fix context_extraction parsing |
| F-078 | P2 | Add context_window fallback |

---

### Phase 3 — P0 Critical Path (4 features, ~2 iterations)
| Feature | Priority | Description | Dependencies |
|---------|----------|-------------|--------------|
| **F-072** | P0 | Error translation in complete() | — |
| **F-073** | P1 | Tests for F-072 | F-072 |
| **F-052** | P0 | Streaming pipeline fix | — |
| F-051 | P0 | Event config safety | — |
| F-050 | P1 | Deny hook enforcement | — |

**⚠️ F-052 and F-072 share same code block — implement together or F-052 first**

---

### Phase 4 — Robustness Hardening (6 features, ~2 iterations)
| Feature | Priority | Description |
|---------|----------|-------------|
| **F-085** | P1 | Timeout (merged with F-058) |
| F-053 | P1 | Unify config loaders |
| F-054 | P1 | Add config reload support |
| F-055 | P1 | Accumulator hardening |
| F-056 | P1 | Lifecycle cleanup |
| **F-082** | P1 | Real SDK path fix (supersedes F-057) |

---

### Phase 5 — Error & Integration Improvements (5 features, ~1-2 iterations)
| Feature | Priority | Description | Order |
|---------|----------|-------------|-------|
| F-066 | P2 | Fix error matching algorithm | First |
| F-061 | P2 | Add new error mappings | After F-066 |
| F-068 | P2 | Event overlap validation | — |
| F-059 | P2 | Multi-turn improvements | — |
| F-086 | P2 | Disconnect tracking | — |

---

### Phase 6 — Retry System (3 features, ~1 iteration)
| Feature | Priority | Description | Notes |
|---------|----------|-------------|-------|
| F-075 | P2 | Delete dead retry.yaml | First |
| F-060 | P2 | Implement config-driven retry | Creates new retry.yaml |
| F-090 | P1 | Test retry behavior | TDD pair with F-060 |

---

### Phase 7 — Structural Refactoring (7 features, ~2 iterations)
| Feature | Priority | Description | Notes |
|---------|----------|-------------|-------|
| **F-088** | P2 | SDK import quarantine | First of quarantine pair |
| F-063 | P2 | Broader SDK quarantine | After F-088 |
| F-069 | P2 | Dead code removal | — |
| F-070 | P2 | Platform detection removal | — |
| **F-071+F-089** | P2 | SessionConfig cleanup | **IMPLEMENT TOGETHER** |
| F-087 | P2 | Type strengthening | — |

---

### Phase 8 — Provider Decomposition (1 feature, ~1-2 iterations)
| Feature | Priority | Description | Notes |
|---------|----------|-------------|-------|
| **F-065** | P2 | Extract completion.py/response.py | **MUST BE LAST provider.py change** |

**⚠️ All features that touch provider.py must land before F-065**

---

### Phase 9 — Test & Packaging Polish (7 features, ~1-2 iterations)
| Feature | Priority | Description |
|---------|----------|-------------|
| F-062 | P2 | Architecture test hardening |
| F-067 | P3 | Test quality improvements |
| F-076 | P3 | Async mock warning fix |
| F-083 | P3 | Enum type fix |
| F-091 | P1 | Ephemeral session tests |
| F-064 | P2 | PyPI readiness |
| F-080 | P2 | Bundle.md and metadata |

---

## SECTION 6: FILE CONFLICT RISK MAP

| File | Features | Risk Level |
|------|----------|------------|
| **provider.py** | F-052, F-054, F-059, F-065, F-067, F-069, F-070, F-072, F-078, F-082, F-084, F-085, F-087 | **CRITICAL (13 features)** |
| **sdk_adapter/client.py** | F-050, F-053, F-056, F-081, F-086, F-088 | **HIGH (6 features)** |
| **sdk_adapter/types.py** | F-071, F-089 | **HIGH (must coordinate)** |
| **config/** | F-074, F-075, F-078, F-060, F-061 | **HIGH (F-074 must go first)** |
| **streaming.py** | F-051, F-055, F-068 | **MEDIUM (3 features)** |
| **error_translation.py** | F-053, F-061, F-066 | **MEDIUM (3 features)** |

---

## SECTION 7: KERNEL COMPLIANCE MATRIX

From core-expert analysis:

| Category | Compliant | Violations |
|----------|-----------|------------|
| Provider Protocol | 38/43 | F-072, F-073, F-052 (type names) |
| Error Types | 40/43 | F-072, F-073 (LLMProviderError doesn't exist) |
| Event Types | 43/43 | All compliant |
| Session Lifecycle | 42/43 | F-071 (removing fields without kernel validation) |
| Type Shadowing | 41/43 | F-052 (TextContent), F-087 (needs ChatRequest source verification) |

---

## SECTION 8: RECOMMENDED ACTIONS

### Before Autonomous Execution

1. **AMEND F-072 and F-073** — Change `LLMProviderError` → `ProviderUnavailableError`
2. **AMEND F-052** — Change `TextContent` → `TextBlock`, verify SDK streaming support
3. **CREATE F-092** — Delete `src/amplifier_module_provider_github_copilot/` directory
4. **DROP F-057** — Superseded by F-082
5. **MERGE F-058 into F-085** — Both add same timeout
6. **VERIFY SDK** — Check if streaming is supported before Phase 3

### During Autonomous Execution

1. **Implement F-052 and F-072 together** — Same code block
2. **Implement F-071 and F-089 together** — Same type definition
3. **F-065 MUST be last provider.py change** — All 13 features must land first
4. **F-074 MUST be before any config features** — Everything depends on it

---

## SECTION 9: FEATURE REGISTRY (Final State)

### DROPPED Features (4)
- **F-057** — Superseded by F-082
- **F-058** — Merged into F-085
- (F-063 and F-064 NOT dropped, just resequenced)

### BLOCKED Features (3 — require spec amendments)
- **F-052** — Needs SDK verification + type fixes
- **F-072** — Needs type name fix
- **F-073** — Needs type name fix

### READY Features (36)
All other features F-049 to F-091 minus dropped/blocked

### NEW Features Needed (0)
- ~~F-092~~ — NOT NEEDED (F-049 already covers path fixes)

---

## SECTION 10: VERDICT

| Gate | Status | Notes |
|------|--------|-------|
| Duplicates Resolved | ⚠️ PENDING | 4 pairs identified, need spec updates |
| Conflicts Resolved | ⚠️ PENDING | 4 conflicts identified, need ordering decisions |
| Gaps Filled | ✅ READY | F-049 covers path fixes |
| Kernel Compliance | ❌ BLOCKED | 3 specs need type fixes |
| Ordering Defined | ✅ READY | 9-phase plan documented |

### Recommendation

**DO NOT execute autonomous dev-machine until:**
1. Blockers 2-3 are resolved (F-072, F-073, F-052 type fixes)
2. F-057 is marked dropped in STATE.yaml
3. F-058 is merged into F-085
4. External reviewer validates this document

**Expert Panel Corrections Applied:**
- Blocker 1 revised: Path drift in tests/specs, NOT dual codebases — F-049 handles this
- F-092 NOT needed — removed from gaps (no directory to delete)
- F-052 type correction: TextContent → ContentBlock (verify exact kernel type from `amplifier_core.types`)

---

## Appendix A: Expert Panel Participants

| Expert | Agent ID | Analysis Scope |
|--------|----------|----------------|
| Architectural Alignment | foundation:zen-architect | Three-Medium Architecture, scope creep, duplicates |
| Ecosystem Alignment | amplifier:amplifier-expert | Kernel integration, reference provider comparison |
| Dependency Analysis | foundation:integration-specialist | DAG, ordering, file conflicts |
| Kernel Compliance | core:core-expert | Protocol, types, errors, events |

---

## Appendix B: Document History

| Date | Action | By |
|------|--------|-----|
| 2026-03-15 | Initial creation from expert panel synthesis | Principal Engineer + Copilot |
| 2026-03-15 | Expert panel validation (zen-architect, amplifier-expert) | Copilot |
| 2026-03-15 | Applied corrections: path drift, F-092 removal, type clarifications | Copilot |
| — | Awaiting external review | — |

---

**END OF CONSOLIDATED FINDINGS**
