# Principal Engineering Review: Spec Audit & Consolidated Findings

**Reviewer:** Principal Engineer (20 years experience) via GitHub Copilot (Claude Opus 4.5)
**Date:** 2026-03-15
**Review Scope:** 
- CONSOLIDATED-FINDINGS.md (Expert Panel Synthesis)
- spec-audit-f001-f091-by-copilot-opus-4-5-2026-03-14.md (Constitutional Review)
- Full codebase verification against claims

**Review Method:** Evidence-based verification with code archaeology, contract analysis, SDK capability audit, and dev-machine configuration review.

---

## Executive Summary: Review Verdict

| Document | Assessment | Verdict |
|----------|------------|---------|
| CONSOLIDATED-FINDINGS.md | **MOSTLY SOUND** with 3 critical corrections needed | APPROVE WITH AMENDMENTS |
| spec-audit-f001-f091-by-copilot-opus-4-5-2026-03-14.md | **CONTAINS ERRORS** in file count; structural findings valid | APPROVE WITH CORRECTIONS |

**Bottom Line:** The expert panel did rigorous work. The implementation plan is executable with the amendments below. The dev-machine CAN proceed after addressing the 6 MANDATORY pre-implementation fixes I identify.

---

## Part 1: CRITICAL CORRECTIONS TO CONSOLIDATED-FINDINGS

### CORRECTION 1: The `src/` Directory DOES Exist (BLOCKER 1 Is Wrong)

**Claim in CONSOLIDATED-FINDINGS:**
> "the `src/` path doesn't exist as a directory"

**VERIFIED REALITY:**
```powershell
PS> Test-Path "d:\next-get-provider-github-copilot\src"
True

PS> Get-ChildItem "d:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot"
    Directory: D:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot
    
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d----          2026-03-13    09:15                __pycache__
d----          2026-03-13    09:15                sdk_adapter

PS> Get-ChildItem "d:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot\sdk_adapter"
    Directory: D:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot\sdk_adapter
    
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d----          2026-03-13    09:15                __pycache__
```

**The actual situation:**
- The `src/amplifier_module_provider_github_copilot/` directory tree EXISTS
- It contains ONLY `__pycache__/` artifacts — no actual Python source files
- This is the remnant of a path migration that left orphan cache directories

**Impact Assessment:**
- Architecture tests DO scan an existing directory (not non-existent as claimed)
- BUT the directory contains zero `.py` files
- Tests pass vacuously because `Path.glob("*.py")` yields zero files, not because the path doesn't exist
- F-049 FIX IS STILL CORRECT — change the path to `amplifier_module_provider_github_copilot/`

**ADDITIONAL FIX REQUIRED:** Delete the `src/` directory tree to prevent confusion:
```powershell
Remove-Item -Recurse -Force "src"
```

This should be done BEFORE F-049 to ensure a clean state.

---

### CORRECTION 2: Spec File Count Is Wrong (90 Files, Not 73)

**Claim in spec-audit:**
> "Total Specs Found: 73 files (F-001 to F-091 with gaps)"

**VERIFIED REALITY:**
```powershell
PS> (Get-ChildItem -Path "specs\features" -Filter "F-*.md").Count
90
```

**Breakdown:**
- 90 total spec files in `specs/features/`
- 4 duplicate numbers (F-002, F-003, F-004, F-005 × 2 = 8 files for 4 numbers)
- 86 unique feature numbers represented
- Missing numbers: F-039, F-040, F-041, F-042 (confirmed)
- F-047 is in `specs/` (not `specs/features/`) — this is the 91st spec file

**Corrected Summary:**
| Metric | Claimed | Actual |
|--------|---------|--------|
| Total Files | 73 | 90 (+ F-047 in wrong location = 91) |
| Duplicate Numbers | 4 | 4 ✓ (correct) |
| Missing Numbers | 4 | Partially wrong — see below |

**Missing Numbers Clarification:**
- F-039-sdk-client-wiring → EXISTS in STATE.yaml as `completed_features`
- F-040-sdk-api-fix → EXISTS in STATE.yaml as `completed_features`
- F-041, F-042 → TRULY MISSING (no file, no STATE.yaml reference)
- F-043 onwards → EXISTS as files

**CONCLUSION:** The audit counted wrong. The structural findings are still valid.

---

### CORRECTION 3: SDK Does NOT Have `send_message()` AsyncIterator (F-052 BLOCKER)

**F-052 Spec Assumes:**
> "Replace `send_and_wait()` with streaming message send + event iteration"

The spec implies using an async iterator pattern like:
```python
async for sdk_event in session.send_message(request.prompt, request.tools):
    ...
```

**VERIFIED SDK REALITY (copilot-sdk/python/copilot/session.py):**

The SDK provides:
1. `send(options)` → non-blocking send, returns message ID only
2. `send_and_wait(options, timeout)` → blocking call, returns final SessionEvent
3. `on(handler)` → event subscription via callback

**NO `send_message()` method exists that returns an AsyncIterator.**

The test path in `provider.py:271-273` uses:
```python
async for sdk_event in session.send_message(request.prompt, request.tools):
```
This works ONLY because tests mock `session.send_message` — the real SDK has no such method.

**Impact on F-052:**
- The implementation approach in F-052 IS INVALID
- F-052 must be REDESIGNED to use `send()` + `on()` event subscription pattern
- OR the provider must continue using `send_and_wait()` with proper error handling (F-072)

**MANDATORY ACTION:** Before implementing F-052:
1. Verify exact SDK API by testing with real copilot CLI
2. If streaming is via event callbacks, redesign F-052 for callback pattern
3. If streaming is not supported, DEFER F-052 and focus on F-072 (error translation for blocking path)

---

### CORRECTION 4: Path Drift Is MORE Severe Than Documented

The documents mention path drift in tests and specs. The actual scope is:

| File | Line | Bad Path | Should Be |
|------|------|----------|-----------|
| `contracts/provider-protocol.md` | 5 | `src/amplifier_module...` | `amplifier_module...` |
| `contracts/error-hierarchy.md` | 5 | `src/amplifier_module...` | `amplifier_module...` |
| `contracts/event-vocabulary.md` | 5 | `src/amplifier_module...` | `amplifier_module...` |
| `contracts/sdk-boundary.md` | 5 | `src/amplifier_module...` | `amplifier_module...` |
| `contracts/streaming-contract.md` | 5 | `src/amplifier_module...` | `amplifier_module...` |
| `contracts/deny-destroy.md` | 5 | `modules/provider-core/session_factory.py` | `amplifier_module.../sdk_adapter/client.py` |
| `tests/test_contract_deny_destroy.py` | 81 | `src/amplifier_module...` | `amplifier_module...` |
| `tests/test_sdk_client.py` | 191 | `src/amplifier_module...` | `amplifier_module...` |
| `specs/features/F-001...` | various | `src/amplifier_module...` | `amplifier_module...` |
| `specs/features/F-002...` | various | `src/amplifier_module...` | `amplifier_module...` |
| `specs/features/F-003...` | various | `src/amplifier_module...` | `amplifier_module...` |

**Note:** `contracts/deny-destroy.md` has a COMPLETELY WRONG path (`modules/provider-core/session_factory.py`) — this references a non-existent structure.

**MANDATORY F-049 EXPANSION:** F-049 should include:
- All 5 contracts Module Reference lines
- All affected spec files (at minimum F-001 through F-010)

---

## Part 2: VALIDATION OF KEY CLAIMS

### VALIDATED: F-072 Real SDK Path Has No Error Translation ✓

**Evidence (provider.py lines 471-489):**
```python
else:
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

**NO try/except block. NO translate_sdk_error() call. F-072 is CONFIRMED P0.**

---

### VALIDATED: provider.close() Is No-Op ✓

**Evidence (provider.py lines 517-523):**
```python
async def close(self) -> None:
    """Clean up provider resources.

    Feature: F-020 AC-1
    """
    # Currently no resources to clean up
    pass
```

**Meanwhile client.close() EXISTS (client.py lines 258-268):**
```python
async def close(self) -> None:
    """Clean up owned client resources. Safe to call multiple times."""
    if self._owned_client is not None:
        try:
            logger.info("[CLIENT] Stopping owned Copilot client...")
            await self._owned_client.stop()
            ...
```

**F-082 is CONFIRMED P1 — resources are leaked.**

---

### VALIDATED: SessionConfig Has Wrong Fields ✓

**Current types.py:**
```python
@dataclass
class SessionConfig:
    model: str
    system_prompt: str | None = None  # ← Wrong name
    max_tokens: int | None = None      # ← Unused
```

**Contract sdk-boundary.md specifies:**
```python
@dataclass
class SessionConfig:
    model: str
    system_message: str | None = None   # ← Correct name
    tools: list[dict[str, Any]] | None = None
    reasoning_effort: str | None = None
```

**F-071 ↔ F-089 conflict is REAL. Resolution needed.**

---

### VALIDATED: F-072/F-073 Reference Non-Existent Type ✓

**F-072 spec line 46:**
> "Red: `sdk_session.send_and_wait()` raises `RuntimeError` → currently bubbles raw → after fix, translated to `LLMProviderError`"

**F-073 spec line 31:**
> "Generic `RuntimeError` → `LLMProviderError` (fallback)"

**error_translation.py line 44 proves `LLMProviderError` does NOT exist:**
```python
from amplifier_core.llm_errors import (
    AbortError,
    AccessDeniedError,
    AuthenticationError,
    ...
    ProviderUnavailableError,  # ← THIS is the correct fallback
    ...
)
```

**MANDATORY:** Amend F-072 and F-073 to use `ProviderUnavailableError` (the actual default fallback per config/errors.yaml).

---

### VALIDATED: _load_error_config_once() Missing context_extraction ✓

**Evidence (client.py lines 82-113):**
```python
def _load_error_config_once() -> ErrorConfig:
    ...
    mappings.append(
        ErrorMapping(
            sdk_patterns=mapping_data.get("sdk_patterns", []),
            string_patterns=mapping_data.get("string_patterns", []),
            kernel_error=mapping_data.get("kernel_error", "ProviderUnavailableError"),
            retryable=mapping_data.get("retryable", True),
            extract_retry_after=mapping_data.get("extract_retry_after", False),
            # ← context_extraction is NOT parsed here
        )
    )
```

**But ErrorMapping dataclass (error_translation.py lines 88-106) HAS:**
```python
@dataclass
class ErrorMapping:
    ...
    context_extraction: list[ContextExtraction] = field(default_factory=_context_list)
```

**F-081 is CONFIRMED P0 — context extraction is silently dropped.**

---

## Part 3: EVALUATION OF IMPLEMENTATION PHASES

### Phase 1 (Zero-Risk Cleanups) — APPROVED ✓

| Feature | Priority | Assessment |
|---------|----------|------------|
| F-049 | P0 | ✓ Correctly prioritized, but scope needs expansion (see Correction 4) |
| F-077 | P3 | ✓ No dependencies, safe cleanup |
| F-079 | P2 | ✓ py.typed marker is standalone |
| F-084 | P3 | ✓ Simple import cleanup |

**AMENDMENT:** Add `rm -rf src/` as a pre-F-049 step.

---

### Phase 2 (Config Foundation) — APPROVED WITH NOTES ✓

| Feature | Priority | Assessment |
|---------|----------|------------|
| F-074 | P0 | ✓ CRITICAL — ALL config loading breaks after wheel install without this |
| F-081 | P0 | ✓ CORRECT P0 — silently drops F-036 functionality |
| F-078 | P2 | ✓ Follows F-074 |

**NOTE:** F-074 is the foundation of config loading. It MUST complete before F-060, F-061, F-066, F-068.

---

### Phase 3 (P0 Critical Path) — NEEDS REDESIGN ⚠️

| Feature | Priority | Assessment |
|---------|----------|------------|
| F-072 | P0 | ✓ VALIDATED — real SDK path has no error translation |
| F-073 | P1 | ✓ Test coverage for F-072 |
| F-052 | P0 | ⚠️ **BLOCKER: SDK API assumption is WRONG** |
| F-051 | P0 | ✓ Event config defensive loading |
| F-050 | P1 | ✓ Deny hook enforcement |

**MANDATORY ACTION FOR F-052:**
1. OPTION A: Redesign to use `send()` + `on()` event callback pattern
2. OPTION B: Defer F-052 and implement F-072 to make blocking path safe
3. OPTION C: Verify if newer SDK versions added an async iterator API

I recommend **OPTION B** — implement F-072 first to ensure the blocking path is safe. Defer F-052 until SDK streaming capabilities are verified with live testing.

---

### Phase 4-9 — APPROVED WITH ORDERING CONSTRAINTS ✓

The remaining phases are well-structured. Key ordering constraints:

1. **F-065 MUST be LAST provider.py change** — 13 features touch this file
2. **F-071 + F-089 MUST be SINGLE UNIT** — they conflict otherwise
3. **F-063 AFTER F-088** — F-088 creates _imports.py, F-063 extends
4. **F-060 vs F-075 decision:** I recommend F-075 first (delete dead retry.yaml), then F-060 creates fresh when needed

---

## Part 4: MANDATORY PRE-IMPLEMENTATION FIXES

Before the dev-machine executes Phase 1, these MUST be addressed:

### FIX 1: Delete Orphan `src/` Directory

```powershell
Remove-Item -Recurse -Force "d:\next-get-provider-github-copilot\src"
```

**Rationale:** Prevents confusion about which path is active. Tests will fail clearly instead of passing vacuously.

---

### FIX 2: Amend F-072 Spec — Type Name Correction

**Change in F-072-real-sdk-path-error-translation.md:**
- Line 46: `LLMProviderError` → `ProviderUnavailableError`
- Implementation Approach: Update example code to use `ProviderUnavailableError`

---

### FIX 3: Amend F-073 Spec — Type Name Correction

**Change in F-073-real-sdk-path-error-test.md:**
- Line 31: `LLMProviderError` → `ProviderUnavailableError`

---

### FIX 4: Amend F-052 Spec — Mark SDK Verification Required

Add to F-052 Problem Statement:
```markdown
## Pre-Implementation Verification Required

**WARNING:** This spec assumes the SDK supports streaming event iteration. 
Verification required before implementation:
1. Test with real copilot CLI: `session.send()` + `on()` pattern vs async iterator
2. If no async iterator API exists, redesign to use event callbacks
3. Alternatively, defer this feature and focus on F-072 (error translation for blocking path)
```

---

### FIX 5: Expand F-049 Scope — Include Contracts

Add to F-049 Files to Modify:
```markdown
## Files to Modify (Expanded)

### Tests
- `tests/test_contract_deny_destroy.py` (line 81)
- `tests/test_sdk_client.py` (line 191)

### Contracts (Module Reference line)
- `contracts/provider-protocol.md` (line 5)
- `contracts/error-hierarchy.md` (line 5)
- `contracts/event-vocabulary.md` (line 5)
- `contracts/sdk-boundary.md` (line 5)
- `contracts/streaming-contract.md` (line 5)
- `contracts/deny-destroy.md` (line 5) — DIFFERENT issue: uses `modules/provider-core/...`

### Early Specs
- `specs/features/F-001-sdk-adapter-skeleton.md`
- `specs/features/F-002-*.md`
- `specs/features/F-003-*.md`
- (All specs referencing `src/amplifier_module_provider_github_copilot`)
```

---

### FIX 6: Resolve F-071 ↔ F-089 Conflict

**DECISION REQUIRED:** Should SessionConfig fields be:
- REMOVED (F-071 approach): Delete `system_prompt`, `max_tokens`
- ALIGNED (F-089 approach): Rename `system_prompt` → `system_message`, add `tools`, `reasoning_effort`

**RECOMMENDATION:** Pursue F-089 (alignment) because:
1. The SDK likely needs these fields for future functionality
2. `system_message` is the canonical kernel naming
3. `tools` is already used in CompletionRequest
4. Removing fields loses optionality; renaming preserves it

**ACTION:** Mark F-071 as `superseded_by: F-089` and amend F-089 to also remove `max_tokens` if truly unused.

---

## Part 5: AGREEMENTS WITH CONSOLIDATED-FINDINGS

### ✓ AGREE: 9-Phase Implementation Order

The phased approach is sound. The dependency analysis correctly identifies:
- F-074 as config foundation
- F-065 as last provider.py change
- Tight coupling between F-052/F-072 and F-071/F-089

### ✓ AGREE: Duplicate Resolution Strategy

| Pair | Resolution | Assessment |
|------|------------|------------|
| F-057 → F-082 | DROP F-057 | ✓ Correct — F-082 has stronger evidence |
| F-058 → F-085 | MERGE | ✓ Correct — both add timeout to same code |
| F-063 ∥ F-088 | F-088 first | ✓ Correct — F-088 creates, F-063 extends |
| F-064 ∥ F-074 | F-074 first | ✓ Correct — F-074 moves config, F-064 is metadata |

### ✓ AGREE: Critical File Conflict Risk

provider.py with 13 features is CRITICAL risk. The recommendation to sequence carefully is correct.

### ✓ AGREE: Kernel Compliance Matrix

The violations identified (F-072, F-073, F-052 type names) are verified correct.

---

## Part 6: DISAGREEMENTS / COUNTER-ARGUMENTS

### DISAGREE: "F-039-041 reserved for future SDK streaming work"

The spec audit suggested F-039-042 might be reserved. STATE.yaml shows:
- F-039-sdk-client-wiring: **COMPLETED**
- F-040-sdk-api-fix: **COMPLETED**
- F-041: TRULY MISSING
- F-042: TRULY MISSING

The correct fix is:
- F-041-TOMBSTONE.md: "Skipped — reserved for future use"
- F-042-TOMBSTONE.md: "Skipped — reserved for future use"

OR audit git history to determine if these were ever created and deleted.

---

### DISAGREE: "No Feature for Deleting src/ Directory"

The CONSOLIDATED-FINDINGS says:
> "F-049 already addresses the path drift issue. No F-092 needed — the src/ path doesn't exist as a directory"

But src/ DOES exist. F-049 only fixes test PATH STRINGS. It does NOT delete the orphan directory.

**COUNTER-PROPOSAL:** Add `rm -rf src/` as a Phase 0 pre-requisite OR as part of F-049 cleanup.

---

### PARTIAL DISAGREE: "SDK Capability Contract Missing" Is Gap

CONSOLIDATED-FINDINGS says:
> "GAP 2: SDK Capability Contract Missing... Recommendation: Create `contracts/sdk-capabilities.md`"

This is accurate, but the PRIORITY is wrong. This should be **P0** because F-052 DEPENDS on knowing SDK capabilities. Without this contract, F-052 cannot be implemented correctly.

**COUNTER-PROPOSAL:** Create `contracts/sdk-capabilities.md` as part of F-052 pre-implementation verification. Don't wait for a separate feature.

---

## Part 7: NEW FINDINGS NOT IN ORIGINAL DOCUMENTS

### NEW FINDING 1: STATE.yaml Blockers Are Accumulating

STATE.yaml has 10+ blocker entries from principal reviews. These are not being processed by the dev-machine. The machine will refuse to execute with blockers present.

**RECOMMENDATION:** Clear blockers by either:
1. Creating a "blocker-resolution" recipe
2. Manually removing blockers after addressing concerns
3. Implementing a "blocker-override" flag for Phase 9 work

---

### NEW FINDING 2: dev-machine Container Requirement May Block Adoption

`.dev-machine/build.yaml` requires running inside Docker:
```yaml
- id: "container-check"
  command: |
    if [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
        ... exit 1
```

This is good for safety but may create friction. Ensure `./run-dev-machine.sh` works correctly.

---

### NEW FINDING 3: Spec Format Migration (F-001-F-038 → Format B) Is P2, Not P3

The spec audit correctly identifies format divergence. But implementing features against Format A specs (no Status/Priority) creates tracking problems.

**COUNTER-PROPOSAL:** Promote spec format migration to P1 and do it in Phase 1 alongside F-049.

---

## Part 8: FINAL RECOMMENDATIONS

### IMMEDIATE (Before Phase 1)

1. **DELETE** `src/` directory (orphan cache only)
2. **AMEND** F-072 spec: `LLMProviderError` → `ProviderUnavailableError`
3. **AMEND** F-073 spec: `LLMProviderError` → `ProviderUnavailableError`
4. **AMEND** F-052 spec: Add SDK verification requirement, consider deferring
5. **EXPAND** F-049 scope: Include all contracts and early specs
6. **RESOLVE** F-071 vs F-089: Mark F-071 superseded by F-089

### RECOMMENDED PHASE ADJUSTMENTS

| Phase | Original | Recommended |
|-------|----------|-------------|
| Phase 0 | (none) | Add: Delete `src/`, clear STATE.yaml blockers |
| Phase 1 | 4 features | Keep + add spec format migration for stability |
| Phase 3 | F-052 P0 | **DEFER F-052** until SDK verification complete |
| Phase 3 | F-072 P0 | **IMPLEMENT FIRST** — makes blocking path safe |

### QUALITY GATES BEFORE EACH PHASE

1. **Before Phase 2:** All config paths verified pointing to correct locations
2. **Before Phase 3:** SDK capabilities documented in `contracts/sdk-capabilities.md`
3. **Before Phase 7:** All Phase 3-6 features verified passing
4. **Before Phase 8:** provider.py total 13 features merged, test coverage > 90%

---

## Part 9: VERDICT

### Spec Audit Document

| Aspect | Finding |
|--------|---------|
| File Count | WRONG (claimed 73, actual 90) |
| Duplicate Detection | CORRECT (4 pairs) |
| Missing Features | PARTIALLY CORRECT (F-039/F-040 exist in STATE.yaml) |
| Path Drift Analysis | CORRECT (underestimated scope) |
| Quality Scoring | VALID methodology |
| Remediation Plan | SOUND |

**VERDICT:** The spec audit provides value despite the count error. The structural findings and remediation plan are executable.

---

### Consolidated Findings Document

| Aspect | Finding |
|--------|---------|
| BLOCKER 1 (path drift) | PARTIALLY WRONG — src/ exists but contains only cache |
| BLOCKER 2 (type violations) | CORRECT — verified |
| BLOCKER 3 (F-052 SDK) | CORRECT — AND WORSE than stated (SDK has no send_message iterator) |
| Duplicate Resolution | CORRECT — verified |
| Conflict Resolution | CORRECT — verified |
| 9-Phase Plan | SOUND — approved with amendments |

**VERDICT:** The consolidated findings are MOSTLY CORRECT. The expert panel did rigorous work. With the 6 mandatory fixes above, the implementation plan is executable.

---

## Part 10: GO/NO-GO DECISION

### GO — WITH CONDITIONS

The dev-machine MAY proceed to Phase 1 **AFTER**:

1. ☐ `src/` directory deleted
2. ☐ F-072 and F-073 specs amended (type name fix)
3. ☐ F-052 marked as BLOCKED pending SDK verification
4. ☐ F-049 scope expanded to include contracts
5. ☐ F-071 marked superseded by F-089
6. ☐ STATE.yaml blockers cleared or overridden

**If Amplifier expert panel disagrees with any correction:** Convene panel review with evidence. The code and SDK are the ground truth — this review cites specific line numbers and verified behaviors.

---

## Appendix A: Evidence Archive

### A.1 provider.py Real SDK Path (Verified No Try/Except)
```
File: amplifier_module_provider_github_copilot/provider.py
Lines: 471-489
Verified: 2026-03-15
Finding: No try/except around sdk_session.send_and_wait()
```

### A.2 SDK Session API (Verified No send_message AsyncIterator)
```
File: copilot-sdk/python/copilot/session.py
Lines: 119-207
Verified: 2026-03-15
Finding: Only send(), send_and_wait(), on() — no send_message() async iterator
```

### A.3 src/ Directory Contents (Verified Exists But Empty)
```
Command: Get-ChildItem -Recurse src/
Verified: 2026-03-15
Finding: Contains __pycache__/ only, no .py files
```

### A.4 Spec File Count (Verified 90 Files)
```
Command: (Get-ChildItem specs/features/F-*.md).Count
Result: 90
Verified: 2026-03-15
```

### A.5 Kernel Error Types (Verified LLMProviderError Absent)
```
File: amplifier_module_provider_github_copilot/error_translation.py
Lines: 44-56
Finding: ProviderUnavailableError exists, LLMProviderError is NOT imported
```

---

## Appendix B: Document Signatures

**This review is intended to serve as the definitive guide for autonomous dev-machine execution.**

If the Amplifier expert panel contests any finding:
1. Cite the specific correction above
2. Provide counter-evidence with file/line references
3. Request panel arbitration

The goal is project success. Let the code be the arbiter.

---

**END OF PRINCIPAL ENGINEERING REVIEW**

*Review conducted with unlimited token budget, deep thinking, and full codebase access.*
*Machine: laptop | Date: 2026-03-15 | Reviewer: Principal Engineer via GitHub Copilot (Claude Opus 4.5)*
