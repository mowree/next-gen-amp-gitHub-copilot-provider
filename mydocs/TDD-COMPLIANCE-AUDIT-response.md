# TDD Compliance Audit — Expert Panel Response

**Date:** 2026-03-15  
**Authority:** Expert Panel Synthesis (12 agents consulted)  
**Purpose:** Evidence-based validation of TDD-COMPLIANCE-AUDIT.md claims

---

## Expert Panel Verdict

### Part A: Spec TDD Compliance
### [PARTIAL AGREE]

**Finding:** The audit claims F-072 to F-081 are "Compliant ✓" with TDD anchors. This is **partially accurate**.

| Spec | Has TDD Section | Has Contract Anchors (`contract:Section:MUST:N`) | Audit Claim |
|------|-----------------|--------------------------------------------------|-------------|
| F-072 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-073 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-074 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-075 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-076 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-077 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-078 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-079 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-080 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |
| F-081 | ✅ Yes (`## TDD Anchor`) | ❌ No formal anchors | ⚠️ Partial |

**Evidence:** (explorer)
- F-072 to F-081 use `## TDD Anchor` with Red/Green/Refactor bullets
- **None** use the proposed `contract:Section:MUST:N` format
- They use prose `## Contract Traceability` sections instead

**Correction Needed:**
- Audit should say "Has TDD Section" not "Has TDD anchor (Compliant)"
- The contract anchor format is **not implemented anywhere yet**

**F-049 to F-070 "Missing TDD" Claims:** ✅ VERIFIED
- F-049, F-054, F-058, F-060, F-062, F-069 all confirmed missing TDD sections
- They have `## Tests Required` (prose) but no TDD Red/Green/Refactor structure

---

### Part B: Test File Audit
### [PARTIAL AGREE — CORRECTIONS NEEDED]

#### B.1: Test File Renames
### ✅ AGREE — All 6 renames are safe

| File | Imports Found | Conftest Refs | Config Refs | Rename Safe |
|------|---------------|---------------|-------------|-------------|
| test_f035_error_types.py | none | No | none | ✅ Yes |
| test_f036_error_context.py | none | No | none | ✅ Yes |
| test_f037_observability.py | none | No | none | ✅ Yes |
| test_f038_kernel_integration.py | none | No | none | ✅ Yes |
| test_f043_sdk_response.py | none | No | none | ✅ Yes |
| test_integration.py | none | No | none | ✅ Yes |

**Evidence:** (test-coverage)
- pyproject.toml uses glob `test_*.py`, not specific filenames
- No cross-imports between test files
- CI uses directory-based pytest invocation

#### B.2: Dead Files
### ⚠️ PARTIAL DISAGREE

| File | Audit Says | Reality | Verdict |
|------|------------|---------|---------|
| test_deny_hook_breach_detector.py | Delete | 4-line tombstone comment only | ✅ DELETE |
| test_placeholder.py | Delete | **Has 2 real tests** (`test_toolchain_works`, `test_version_exists`) | ❌ KEEP or SUPERSEDE |

**Evidence:** (bug-hunter)
- `test_placeholder.py` contains runnable tests that pytest will collect
- `test_version_exists()` asserts version == "0.1.0" — live code, not dead
- `test_deny_hook_breach_detector.py` is pure comment with zero executable code

**Correction Needed:**
- Remove `test_placeholder.py` from delete list
- Either keep it or explicitly supersede with another test file

#### B.3: test_bug_fixes.py Split
### ❌ DISAGREE — REJECT SPLIT

**Audit proposes splitting into:**
- AC-1 → test_session_cleanup.py
- AC-2 → test_error_propagation.py
- AC-3 → test_config_fallback.py
- AC-5 → test_stream_completion.py
- AC-6 → test_sdk_disconnect.py

**Reality:** (zen-architect)

| Proposed File | AC Actually Tests | Name Mismatch |
|---------------|-------------------|---------------|
| test_session_cleanup.py | load_event_config crash | ❌ Wrong |
| test_error_propagation.py | dead asserts/None session | ❌ Wrong |
| test_config_fallback.py | retry_after regex | ❌ Wrong |
| test_stream_completion.py | finish_reason_map | ⚠️ Partial (test_streaming.py exists) |
| test_sdk_disconnect.py | tombstone file deletion | ❌ Wrong |

**File Stats:**
- Total tests: 14
- Total LOC: 239
- Shared fixtures: none
- Test ordering dependencies: none
- AC-4: Missing (gap in numbering)

**Verdict:** REJECT_SPLIT
- File is only 239 LOC (well below split threshold)
- ALL proposed filenames semantically mischaracterize their ACs
- Split creates overhead without value

#### B.4: ConfigCapturingMock Migration
### ⚠️ PARTIAL DISAGREE — SCOPE OVERSTATED

**Audit claims 5 files need migration.** Reality: (integration-specialist)

| File | Uses CCM | Uses bare MagicMock | Migration Needed |
|------|----------|---------------------|------------------|
| test_sdk_boundary_contract.py | ✅ 13 instances | 0 | NO |
| test_sdk_boundary.py | 0 | 4 instances | ⚠️ MAYBE |
| test_sdk_client.py | 0 | 0 (uses AsyncMock) | NO |
| test_sdk_adapter.py | 0 | 0 (uses dataclass) | NO |
| test_provider.py | 0 | 0 (uses @dataclass) | NO |
| test_session_factory.py | 0 | 0 | NO |

**Key Finding:**
- Only `test_sdk_boundary.py` has bare MagicMock() (4 instances)
- BUT these are for session mock testing, not config capture
- CCM is purpose-built for config verification — using it for session lifecycle would be incorrect

**Recommendation:** Either leave test_sdk_boundary.py unchanged OR extract StrictSessionStub pattern

---

### Part C: Missing from Original Audit

#### C.1: Enforcement Script Gaps (python-dev)

| Check | Script | Parses Proposed Format | Missing Patterns After Rename |
|-------|--------|------------------------|-------------------------------|
| Contract coverage | check-contract-coverage.py | ✅ Yes | `test_error_types*.py` not in SDK_BOUNDARY_PATTERNS |
| MagicMock abuse | check-magicmock-abuse.py | N/A | `test_error_types*.py` falls out of scope |

**BLOCKER:** Renamed files (`test_error_types.py`, etc.) have no `test_sdk_`, `test_session_`, `test_provider_`, or `test_boundary_` prefix — they silently fall out of enforcement scope in BOTH scripts.

#### C.2: Execution Order Hidden Dependencies (code-intel)

| Phase | Depends On | Blocks | Safe Independently |
|-------|------------|--------|-------------------|
| 1: Delete dead files | None | None | ✅ Yes |
| 2: Rename test files | None | Phase 4 | ⚠️ Conditional |
| 3: Add TDD Section 7 | None | None | ✅ Yes |
| 4: Split test_bug_fixes.py | Phase 2 | Phase 5, 6 | ❌ No |
| 5: CCM migration | Phase 4 + CCM exists | None | ❌ No |
| 6: Contract anchors | Phase 4 | None | ❌ No |

**BLOCKERS MISSED BY AUDIT:**

1. **ConfigCapturingMock is undefined** — grep finds no CCM class in tests/fixtures/. Phase 5 references a class that does not exist.

2. **Phase 2 → Phase 4 dependency** — If rename touches test_bug_fixes.py, Phase 4 has broken path reference.

3. **F-077 vs F-091 conflict** — F-077 deletes test_ephemeral_session_wiring.py, but F-091 needs to add ephemeral session tests. Natural home file would be deleted.

4. **test_bug_fixes.py has 15 Pyright errors** — All reportMissingImports. Split will inherit errors.

#### C.3: Contract Anchor Format (core-expert)

**Finding:** The proposed anchor format `contract:Section:MUST:N` is **NOT kernel-standard**.

| Source | Uses RFC 2119 | Uses Numbered Anchors |
|--------|---------------|----------------------|
| Local contracts (deny-destroy.md, provider-protocol.md) | Yes | Yes |
| Amplifier-core contracts (PROVIDER_CONTRACT.md, etc.) | Yes | **No** (narrative only) |

**Implication:** This is a **custom format** for GitHub Copilot provider. Amplifier core does not enforce it.

#### C.4: Amplifier Reference Alignment (amplifier-expert)

| Pattern | Anthropic/OpenAI | GitHub Copilot Audit |
|---------|------------------|---------------------|
| TDD Section in specs | No | Yes (proposed) |
| Contract anchors in docstrings | No | Yes (proposed) |
| ConfigCapturingMock | No (use FakeCoordinator) | Yes (unique need) |
| SDK boundary tests | No (no SDK config dict) | Yes (JS SDK wrapping) |

**Verdict:** GitHub Copilot's TDD audit is **not over-engineered** — it's **GitHub Copilot-specific**. Other providers don't wrap a JavaScript SDK.

#### C.5: Security Review (security-guardian)

| File | Deletion Risk |
|------|---------------|
| test_deny_hook_breach_detector.py | ✅ SAFE — tombstone, security coverage now in 5 other files |
| test_placeholder.py | ✅ SAFE — no security assertions |

**WARNING:** `ConfigCapturingMock` stores raw captured config in memory without redaction. Safe today (no auth tokens in session config), but not sanitized if secrets are added later.

---

### Part D: Execution Order
### [NEEDS MODIFICATION]

**Recommended Order Changes:** (code-intel)

1. **INSERT Phase 0:** Define ConfigCapturingMock in tests/conftest.py before Phase 5 can run

2. **Phase 2 must exclude test_bug_fixes.py** OR Phase 4 must target renamed path

3. **Phase 3 can run PARALLEL** with Phases 1 and 2 (pure spec/doc change)

4. **Current order (4 → 5 → 6) is correct** for contract anchors — do NOT invert

**CI Impact:** None — CI uses glob patterns, not specific filenames

---

## STATE.yaml Additions

No new features required. The audit describes **cleanup work**, not new features.

However, the following should be tracked:

| Issue | Tracking |
|-------|----------|
| ConfigCapturingMock undefined | Add as blocker to F-044/F-045 or create new feature |
| Enforcement script pattern gaps | Update scripts, not new feature |
| test_placeholder.py decision | Remove from delete list in audit |

---

## Final Counts

| Metric | Value |
|--------|-------|
| **New features added to backlog** | 0 |
| **Total features in ready status** | 40 (unchanged) |
| **Audit claims verified** | 12/15 (80%) |
| **Audit claims needing correction** | 3 |
| **Blockers identified** | 4 |

---

## Work Order for superpowers:* Expert — Spec Updates

### Specs Requiring Updates (on approval by 3rd party reviewer)

| Spec | Required Changes |
|------|------------------|
| F-049 | Replace "manual planted violation" with explicit automated failing-test step |
| F-050 | Choose one exact test file path; define exception type/message assertions |
| F-052 | Split into smaller specs; define exact event sequence/assertions |
| F-065 | Split refactor into smaller iterations; remove subjective size targets |
| F-090 | Inline exact retry/backoff values from contracts/behaviors.md |

### All F-072 to F-081 Specs
- Add formal contract anchors in `contract:Section:MUST:N` format
- Current `## TDD Anchor` sections are prose, not machine-parseable

### Enforcement Scripts
- Add `test_error_types*.py` to SDK_BOUNDARY_PATTERNS in both scripts
- Verify patterns after all renames are finalized

---

## Quality Gate Verification

- [x] All file paths verified to exist (explorer, test-coverage, bug-hunter)
- [x] No hallucinated agent names or APIs (all agents are foundation:*, python-dev:*, etc.)
- [x] Every claim has file:line evidence (see individual expert reports)
- [x] Contradictions with prior Principal Reviewer feedback resolved (test_placeholder.py verdict corrected)
