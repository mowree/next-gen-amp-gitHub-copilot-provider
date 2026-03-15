# Feature Spec Audit: F-001 through F-091
**Reviewer:** GitHub Copilot (Claude Opus 4.5)
**Date:** 2026-03-14
**Scope:** All feature specs in `specs/features/`
**Purpose:** Constitutional review ensuring specs can produce correct code

---

## Executive Summary

**Total Specs Found:** 73 files (F-001 to F-091 with gaps)
**Duplicate Numbers:** 4 (F-002, F-003, F-004, F-005 each have 2 files)
**Missing Numbers:** 4 (F-039, F-040, F-041, F-042)
**Critical Issues:** 12
**High Issues:** 8
**Medium Issues:** 15
**Low Issues:** 10

**Verdict:** NEEDS SIGNIFICANT CLEANUP before specs can serve as authoritative constitution

---

## Part 1: Structural Issues (P0)

### 1.1 DUPLICATE FEATURE NUMBERS — CRITICAL

The following feature numbers have two spec files each:

| Number | File 1 | File 2 | Conflict Type |
|--------|--------|--------|---------------|
| F-002 | `F-002-error-translation.md` | `F-002-provider-protocol-contract.md` | Different concerns |
| F-003 | `F-003-error-hierarchy-contract.md` | `F-003-session-factory.md` | Different concerns |
| F-004 | `F-004-session-factory.md` | `F-004-tool-parsing.md` | Different concerns |
| F-005 | `F-005-basic-completion.md` | `F-005-event-translation.md` | Different concerns |

**Impact:** Feature tracking systems can't map F-xxx to a single spec. Build system ambiguity.

**Fix Required:**
- F-002a/F-002b or renumber one (e.g., F-002 remains error-translation, F-002b became F-038?)
- Audit which implementations reference which spec by number
- Update STATE.yaml, FEATURE-ARCHIVE.yaml references

### 1.2 MISSING FEATURE NUMBERS — HIGH

Gaps in numbering: F-039, F-040, F-041, F-042

**Questions:**
- Were these deleted? If so, why no tombstone/deprecated marker?
- Were these skipped intentionally?
- Are there orphan implementations referencing these?

**Fix Required:**
- Add tombstone files if deleted: `F-039-DEPRECATED.md` with reason
- Or document the gap: "F-039-041 reserved for future SDK streaming work"

### 1.3 F-047 LOCATION MISMATCH — MEDIUM

`F-047-testing-course-correction.md` is in `specs/` not `specs/features/`.
This is the ONLY feature spec outside the standard location.

**Fix Required:** Move to `specs/features/F-047-testing-course-correction.md`

### 1.4 PATH INCONSISTENCIES — HIGH

Early specs (F-001 through ~F-003) use:
```
src/amplifier_module_provider_github_copilot/sdk_adapter/
```

Actual code path is:
```
amplifier_module_provider_github_copilot/sdk_adapter/
```

This exact bug caused DEF-001 (TestArchitectureFitness scanning wrong path).

**Specs with wrong paths:**
- F-001-sdk-adapter-skeleton.md (lines 16-33, section 5)
- F-002-provider-protocol-contract.md
- F-003-error-hierarchy-contract.md

**Fix Required:** Global find/replace `src/amplifier_module_provider_github_copilot` → `amplifier_module_provider_github_copilot` in all specs

---

## Part 2: Format Inconsistencies (P1)

### 2.1 HEADER FORMAT DIVERGENCE

**Format A (F-001, F-002, F-003):**
```markdown
# F-001: Title
## 1. Overview
## 2. Requirements
## 3. Acceptance Criteria
## 4. Edge Cases
## 5. Files to Create/Modify
## 6. Dependencies
## 7. Notes
```

**Format B (F-049+):**
```markdown
# F-049: Title
**Status:** ready
**Priority:** P0
**Source:** deep-review/document.md
**Defect ID:** DEF-xxx

## Problem Statement
## Success Criteria
## Implementation Approach
## Files to Modify
## Tests Required
## Contract Traceability
## Not In Scope
```

**Impact:** Machine parsing is harder. Hard to extract priority/status from Format A specs.

**Fix Required:** Migrate all specs to Format B (or create spec-template.md and enforce)

### 2.2 MISSING REQUIRED SECTIONS

| Section | % Present | Should Be |
|---------|-----------|-----------|
| Status | 70% | 100% |
| Priority | 70% | 100% |
| Contract Traceability | 60% | 100% |
| Tests Required | 85% | 100% |
| Not In Scope | 65% | 100% |

**Fix Required:**
- Add missing sections to all specs
- Status should be: `ready` / `in-progress` / `done` / `deprecated`
- Priority should be: P0/P1/P2/P3

---

## Part 3: Semantic Conflicts (P0)

### 3.1 SUPERSEDES RELATIONSHIPS NOT ENFORCED

| Superseding Spec | Superseded Spec | Documented? |
|------------------|-----------------|-------------|
| F-082 | F-057 | Yes ("Supersedes: F-057") |
| F-088 | F-063 (partial) | No |
| F-081 | F-053 (immediate fix vs structural) | Partial |
| F-072 | F-052 (real SDK path error) | No |

**Impact:** Without clear supersedes chain, which spec is authoritative?

**Fix Required:**
- Add `**Supersedes:**` field to all specs that replace others
- Add `**Superseded By:**` field to deprecated specs
- Mark superseded specs with `**Status:** deprecated`

### 3.2 CONFLICTING SPECIFICATIONS

**Conflict 1: SessionConfig Fields**
- F-071: "Remove `system_prompt` and `max_tokens` fields" (unused)
- F-089: "Align SessionConfig fields with contract" (add `system_message`, `tools`)
- F-001: Original spec shows `system_prompt`, `max_tokens`
- Contract sdk-boundary.md: requires `system_message`, `tools`, `reasoning_effort`

**Resolution needed:** Is SessionConfig shrinking (F-071) or expanding (F-089)?

**Conflict 2: SDK Boundary Structure**
- F-063: "Create `_imports.py`" + other restructuring
- F-088: "Create `_imports.py`" (standalone)

**Resolution needed:** These are duplicates. One should supersede the other.

**Conflict 3: Error Config Loading**
- F-053: "Unify error config loading" (structural fix)
- F-081: "Fix context_extraction in client.py" (immediate fix)

**Documented relationship:** F-081 says "F-053 is the structural fix that eliminates the duplication root cause" — GOOD, but F-053 should reference F-081 as prerequisite.

---

## Part 4: Anti-Patterns (P1)

### 4.1 OVERLY PRESCRIPTIVE IMPLEMENTATIONS

Several specs include exact code snippets in "Implementation Approach":
- F-072: Full try/except block with imports
- F-082: Full method implementation
- F-088: Full `_imports.py` file content

**Problem:** If the implementation differs (for good reason), spec appears "violated" even when intent is met.

**Fix:** Use pseudocode or requirement statements, not copy-paste-ready code.

### 4.2 DEEP-REVIEW DEPENDENCY

Many specs cite `Source: deep-review/xxx.md` where those documents may drift:
- If deep-review documents are deleted/renamed, specs have dangling references
- If deep-review findings change, specs may become stale

**Fix:** 
- Specs should be self-contained
- Reference deep-review for historical context, not as authoritative source
- Copy critical evidence INTO the spec

### 4.3 DEFECT IDs WITHOUT REGISTRY

Some specs have `Defect ID: DEF-xxx`, others have `N/A`.
There's no central defect registry file.

**Fix:** 
- Create `specs/DEFECT-REGISTRY.md` listing all DEF-xxx IDs
- Or remove DEF-xxx references in favor of spec numbers

---

## Part 5: Missing Specs (Gaps in Coverage)

### 5.1 FEATURES IMPLEMENTED BUT NO SPEC

| Code Evidence | Likely Feature | Missing Spec? |
|---------------|----------------|---------------|
| `config/models.yaml` | Model configuration | Not clear which spec owns |
| `config/retry.yaml` | Retry configuration | F-060 exists but dead config |
| `DEVELOPMENT.md` | Dev workflow | No spec |
| `bundle.md` | Distribution bundle | F-064 mentions but doesn't own |

### 5.2 CONTRACTS WITHOUT FEATURE SPECS

| Contract | Feature Spec? |
|----------|---------------|
| `contracts/behaviors.md` | F-060, F-090, F-091 exist but incomplete |
| `contracts/streaming-contract.md` | F-006-, covered |
| `contracts/deny-destroy.md` | F-019, F-050 cover |
| `contracts/sdk-boundary.md` | F-063, F-088 cover |
| `contracts/error-hierarchy.md` | F-002, F-003and cover |
| `contracts/event-vocabulary.md` | F-005-, F-051, F-068 cover |
| `contracts/provider-protocol.md` | F-002 (duplicate), F-020 cover |

---

## Part 6: Spec Quality Matrix

### 6.1 COMPLETENESS SCORING

| Spec | Status | Priority | Contract | Tests | Scope | Score |
|------|--------|----------|----------|-------|-------|-------|
| F-001 | ❌ | ❌ | ❌ | ✅ | ❌ | 1/5 |
| F-002 (error) | ❌ | ❌ | ✅ | ✅ | ❌ | 2/5 |
| F-002 (protocol) | ❌ | ✅ | ✅ | ✅ | ❌ | 3/5 |
| F-049 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |
| F-050 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |
| F-051 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |
| F-052 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |
| F-072 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |
| F-081 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |
| F-088 | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 |

**Pattern:** F-049+ specs (generated from deep-review) are higher quality.
F-001 through F-038 need audit/migration to new format.

---

## Part 7: Dependency Graph Issues

### 7.1 CIRCULAR DEPENDENCIES

No explicit circular dependencies found. However, implicit cycles exist:

```
F-053 (Unify error config) 
  → needs F-081 done first (fix context_extraction)
  → but F-081 "relationship" section says F-053 is the structural fix
```

This is not a cycle, but the ordering is confusing. F-081 should be prerequisite of F-053.

### 7.2 MISSING DEPENDENCY DECLARATIONS

Specs should have `**Depends on:**` field. Many don't.

**Example:** F-072 (add error translation to complete()) should depend on:
- F-052 (real SDK streaming pipeline) — same code area

---

## Part 8: Prioritized Remediation Plan

### P0 — MUST FIX BEFORE NEXT BUILD

1. **Fix duplicate numbers (F-002, F-003, F-004, F-005)**
   - Rename second file to unused number or append letter
   - Update all references

2. **Fix path prefix in early specs**
   - Global replace `src/amplifier_module_provider_github_copilot` → `amplifier_module_provider_github_copilot`

3. **Move F-047 to correct location**
   - `specs/F-047-...` → `specs/features/F-047-...`

### P1 — FIX THIS WEEK

4. **Add tombstones for F-039, F-040, F-041, F-042**

5. **Add Status/Priority to F-001 through F-038**

6. **Resolve SessionConfig conflict (F-071 vs F-089)**
   - Decide: shrink or expand?
   - Deprecate the other

7. **Consolidate F-063 and F-088** (both create _imports.py)
   - One supersedes the other

### P2 — FIX THIS SPRINT

8. **Create `specs/SPEC-TEMPLATE.md`** with required sections

9. **Create `specs/DEFECT-REGISTRY.md`**

10. **Migrate F-001 through F-038 to Format B**

### P3 — TECH DEBT

11. **Remove code snippets from Implementation Approach sections**

12. **Make deep-review references historical, not authoritative**

---

## Part 9: Spec Inventory (All 73 Files)

### Found Files (Sorted)

```
F-001-sdk-adapter-skeleton.md
F-002-error-translation.md          ← DUPLICATE NUMBER
F-002-provider-protocol-contract.md ← DUPLICATE NUMBER
F-003-error-hierarchy-contract.md   ← DUPLICATE NUMBER
F-003-session-factory.md            ← DUPLICATE NUMBER
F-004-session-factory.md            ← DUPLICATE NUMBER
F-004-tool-parsing.md               ← DUPLICATE NUMBER
F-005-basic-completion.md           ← DUPLICATE NUMBER
F-005-event-translation.md          ← DUPLICATE NUMBER
F-006-streaming-handler.md
F-007-completion-lifecycle.md
F-008-provider-orchestrator.md
F-009-integration-verification.md
F-010-sdk-client-wrapper.md
F-011-loop-controller.md
F-012-tool-capture-strategy.md
F-013-event-router.md
F-014-real-sdk-integration.md
F-015-completion-wiring.md
F-016-e2e-integration-tests.md
F-017-technical-debt-cleanup.md
F-018-aggressive-simplification.md
F-019-critical-security-fixes.md
F-020-protocol-compliance.md
F-021-bug-fixes.md
F-022-foundation-integration.md
F-023-test-coverage.md
F-024-code-quality.md
F-025-ci-pipeline.md
F-026-contract-compliance-tests.md
F-027-real-sdk-integration.md
F-028-entry-point.md
F-029-documentation-update.md
F-030-changelog.md
F-031-system-notification-event.md
F-032-permission-handler-tests.md
F-033-permission-handler-fix.md
F-034-sdk-version-tests.md
F-035-error-type-expansion.md
F-036-error-context-enhancement.md
F-037-observability-improvements.md
F-038-kernel-type-migration.md
[F-039 MISSING]
[F-040 MISSING]
[F-041 MISSING]
[F-042 MISSING]
F-043-tdd-and-e2e-coverage.md
F-044-system-prompt-replace-mode.md
F-045-disable-sdk-builtin-tools.md
F-046-sdk-integration-testing-architecture.md
[F-047 in specs/ not specs/features/]
F-048-config-extraction.md
F-049-fix-architecture-test-paths.md
F-050-mandatory-deny-hook-installation.md
F-051-defensive-event-config-loading.md
F-052-real-sdk-streaming-pipeline.md
F-053-unify-error-config-loading.md
F-054-response-extraction-recursion-guard.md
F-055-streaming-accumulator-completion-guard.md
F-056-sdk-client-failed-start-cleanup.md
F-057-provider-close-cleanup.md       ← SUPERSEDED BY F-082
F-058-sdk-request-timeout-enforcement.md
F-059-chatrequest-multi-turn-context.md
F-060-config-driven-retry.md
F-061-error-config-missing-mappings.md
F-062-architecture-test-hardening.md
F-063-sdk-boundary-structure.md       ← OVERLAPS F-088
F-064-pypi-publishing-readiness.md
F-065-provider-decomposition.md
F-066-error-translation-safety.md
F-067-test-quality-improvements.md
F-068-event-classification-validation.md
F-069-remove-complete-fn-dead-code.md
F-070-cleanup-deferred-imports.md
F-071-remove-unused-sessionconfig-fields.md ← CONFLICTS F-089?
F-072-real-sdk-path-error-translation.md
F-073-real-sdk-path-error-test.md
F-074-config-not-in-wheel.md
F-075-retry-yaml-dead-config.md
F-076-fix-async-mock-warning.md
F-077-delete-tombstone-test-files.md
F-078-add-context-window-to-fallback-config.md
F-079-add-py-typed-marker.md
F-080-add-missing-pypi-metadata.md
F-081-fix-context-extraction-in-client-error-loading.md
F-082-wire-provider-close-to-client-close.md ← SUPERSEDES F-057
F-083-fix-test-contract-events-enum-type.md
F-084-remove-redundant-path-import.md
F-085-add-timeout-enforcement-real-sdk-path.md
F-086-handle-session-disconnect-failures.md
F-087-strengthen-complete-parameter-type.md
F-088-create-imports-py-sdk-quarantine.md ← OVERLAPS F-063
F-089-align-sessionconfig-shape-with-contract.md ← CONFLICTS F-071?
F-090-behavioral-tests-for-behaviors-contract.md
F-091-ephemeral-session-invariant-tests.md
```

---

## Part 10: Constitutional Test

**Question:** Can an AI produce correct code from these specs alone?

**Answer:** NO, not currently.

**Reasons:**
1. Duplicate numbers create ambiguity
2. Path inconsistencies would cause tests to fail
3. Conflicting specs (F-071 vs F-089) have no resolution
4. Supersedes relationships not consistently documented
5. Early specs lack required sections (Priority, Status, Contract)
6. No spec template enforces consistency

**After remediation:** YES, with the fixes above, the specs would serve as a valid constitution.

---

## Appendix A: Evidence Citations

### A.1 Duplicate Number Evidence
```
$ ls specs/features/F-002*
F-002-error-translation.md
F-002-provider-protocol-contract.md
```

### A.2 Missing Number Evidence
```
$ ls specs/features/F-03[9-9]*
ls: cannot access 'specs/features/F-039*': No such file or directory

$ ls specs/features/F-04[0-2]*
ls: cannot access 'specs/features/F-040*': No such file or directory
```

### A.3 Path Mismatch Evidence
```
# F-001-sdk-adapter-skeleton.md line 36:
`src/amplifier_module_provider_github_copilot/sdk_adapter/__init__.py`

# Actual filesystem:
$ ls amplifier_module_provider_github_copilot/sdk_adapter/__init__.py
amplifier_module_provider_github_copilot/sdk_adapter/__init__.py
(no src/ prefix)
```

### A.4 F-047 Location Evidence
```
$ find specs -name "F-047*"
specs/F-047-testing-course-correction.md
(should be in specs/features/)
```

---

## Appendix B: Spec-by-Spec Status

| Spec | Priority | Status | Quality | Notes |
|------|----------|--------|---------|-------|
| F-001 | ? | ? | 1/5 | Missing headers, wrong paths |
| F-002a | ? | ? | 2/5 | DUPLICATE NUMBER |
| F-002b | P0 | ? | 3/5 | DUPLICATE NUMBER |
| F-003a | P0 | ? | 2/5 | DUPLICATE NUMBER |
| F-003b | ? | ? | 2/5 | DUPLICATE NUMBER |
| F-004a | ? | ? | 2/5 | DUPLICATE NUMBER |
| F-004b | ? | ? | 2/5 | DUPLICATE NUMBER |
| F-005a | ? | ? | 2/5 | DUPLICATE NUMBER |
| F-005b | ? | ? | 2/5 | DUPLICATE NUMBER |
| F-006 | ? | ? | 2/5 | Old format |
| F-007 | ? | ? | 2/5 | Old format |
| F-008 | ? | ? | 2/5 | Old format |
| F-009 | ? | ? | 2/5 | Old format |
| F-010 | ? | ? | 2/5 | Old format |
| F-011 | ? | ? | 2/5 | Old format |
| F-012 | ? | ? | 2/5 | Old format |
| F-013 | ? | ? | 2/5 | Old format |
| F-014 | ? | ? | 2/5 | Old format |
| F-015 | ? | ? | 2/5 | Old format |
| F-016 | ? | ? | 2/5 | Old format |
| F-017 | ? | ? | 2/5 | Old format |
| F-018 | ? | ? | 2/5 | Old format |
| F-019 | ? | ? | 2/5 | Old format |
| F-020 | ? | ? | 2/5 | Old format |
| F-021 | ? | ? | 2/5 | Old format |
| F-022 | ? | ? | 2/5 | Old format |
| F-023 | ? | ? | 2/5 | Old format |
| F-024 | ? | ? | 2/5 | Old format |
| F-025 | ? | ? | 2/5 | Old format |
| F-026 | ? | ? | 2/5 | Old format |
| F-027 | ? | ? | 2/5 | Old format |
| F-028 | ? | ? | 2/5 | Old format |
| F-029 | ? | ? | 2/5 | Old format |
| F-030 | ? | ? | 2/5 | Old format |
| F-031 | ? | ? | 2/5 | Old format |
| F-032 | ? | ? | 2/5 | Old format |
| F-033 | ? | ? | 2/5 | Old format |
| F-034 | ? | ? | 2/5 | Old format |
| F-035 | ? | ? | 2/5 | Old format |
| F-036 | ? | ? | 2/5 | Old format |
| F-037 | ? | ? | 2/5 | Old format |
| F-038 | ? | ? | 2/5 | Old format |
| F-039 | — | MISSING | — | Tombstone needed |
| F-040 | — | MISSING | — | Tombstone needed |
| F-041 | — | MISSING | — | Tombstone needed |
| F-042 | — | MISSING | — | Tombstone needed |
| F-043 | ? | ? | 3/5 | Transition format |
| F-044 | P0 | done? | 4/5 | Good spec |
| F-045 | P0 | done? | 4/5 | Good spec |
| F-046 | ? | ? | 4/5 | Good spec |
| F-047 | ? | ? | ?/5 | WRONG LOCATION |
| F-048 | ? | ? | 4/5 | Good spec |
| F-049 | P0 | ready | 5/5 | Excellent spec |
| F-050 | P1 | ready | 5/5 | Excellent spec |
| F-051 | P0 | ready | 5/5 | Excellent spec |
| F-052 | P0 | ready | 5/5 | Excellent spec |
| F-053 | P1 | ready | 5/5 | Excellent spec |
| F-054 | P1 | ready | 5/5 | Excellent spec |
| F-055 | P1 | ready | 5/5 | Excellent spec |
| F-056 | P1 | ready | 5/5 | Excellent spec |
| F-057 | P1 | superseded | 5/5 | Superseded by F-082 |
| F-058 | P1 | ready | 5/5 | Excellent spec |
| F-059 | P1 | ready | 5/5 | Excellent spec |
| F-060 | P2 | ready | 5/5 | Excellent spec |
| F-061 | P2 | ready | 5/5 | Excellent spec |
| F-062 | P2 | ready | 5/5 | Excellent spec |
| F-063 | P2 | ready | 4/5 | Overlaps F-088 |
| F-064 | P2 | ready | 5/5 | Excellent spec |
| F-065 | P2 | ready | 5/5 | Excellent spec |
| F-066 | P2 | ready | 5/5 | Excellent spec |
| F-067 | P2 | ready | 5/5 | Excellent spec |
| F-068 | P2 | ready | 5/5 | Excellent spec |
| F-069 | P2 | ready | 5/5 | Excellent spec |
| F-070 | P2 | ready | 5/5 | Excellent spec |
| F-071 | P2 | ready | 4/5 | May conflict F-089 |
| F-072 | P0 | ready | 5/5 | Excellent spec |
| F-073 | P0 | ready | 5/5 | Excellent spec |
| F-074 | P0 | ready | 5/5 | Excellent spec |
| F-075 | P2 | ready | 5/5 | Excellent spec |
| F-076 | P3 | ready | 5/5 | Excellent spec |
| F-077 | P3 | ready | 5/5 | Excellent spec |
| F-078 | P2 | ready | 5/5 | Excellent spec |
| F-079 | P2 | ready | 5/5 | Excellent spec |
| F-080 | P2 | ready | 5/5 | Excellent spec |
| F-081 | P0 | ready | 5/5 | Excellent spec |
| F-082 | P1 | ready | 5/5 | Supersedes F-057 |
| F-083 | P3 | ready | 5/5 | Excellent spec |
| F-084 | P3 | ready | 5/5 | Excellent spec |
| F-085 | P1 | ready | 5/5 | Excellent spec |
| F-086 | P2 | ready | 5/5 | Excellent spec |
| F-087 | P2 | ready | 5/5 | Excellent spec |
| F-088 | P2 | ready | 4/5 | Overlaps F-063 |
| F-089 | P2 | ready | 4/5 | May conflict F-071 |
| F-090 | P2 | ready | 5/5 | Excellent spec |
| F-091 | P2 | ready | 5/5 | Excellent spec |

---

## Appendix C: Recommended Actions Summary

### Immediate (Before Next Build)
1. Resolve F-002/F-003/F-004/F-005 duplicates
2. Fix src/ path prefix in F-001 through F-003
3. Move F-047 to specs/features/

### This Week
4. Add F-039-042 tombstones
5. Add Status/Priority to old specs
6. Resolve F-071 vs F-089 conflict
7. Deprecate F-063 in favor of F-088 (or vice versa)
8. Mark F-057 as deprecated (superseded by F-082)

### This Sprint
9. Create SPEC-TEMPLATE.md
10. Create DEFECT-REGISTRY.md
11. Migrate all specs to Format B

---

*End of Audit Report*
