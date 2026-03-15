# Spec Audit: F-049 through F-071

**Date:** 2026-03-15
**Auditor:** zen-architect
**Scope:** All 23 Phase 9 feature specs

## Audit Criteria

| # | Criterion | Description |
|---|-----------|-------------|
| 1 | Problem Statement | Clear description with evidence (file:line references) |
| 2 | Success Criteria | Testable checkboxes |
| 3 | Implementation Approach | High-level but actionable |
| 4 | Files to Modify | Exact paths |
| 5 | Tests Required | Specific test files/functions |
| 6 | Not In Scope | What this does NOT address |
| 7 | TDD Approach | Red-Green-Refactor steps inferable from spec |
| 8 | Contract Traceability | Links to contracts/ documents |

## Summary Table

| Spec | Problem | Success | Approach | Files | Tests | Scope | TDD | Contract | Status |
|------|---------|---------|----------|-------|-------|-------|-----|----------|--------|
| F-049 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-050 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-051 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-052 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-053 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-054 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-055 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-056 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-057 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-058 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-059 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-060 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-061 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-062 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-063 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-064 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-065 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-066 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-067 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-068 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-069 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-070 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |
| F-071 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **PASS** |

**Result: 23/23 specs PASS all 8 criteria**

## Fixes Applied During Audit

The following deficiencies were found and corrected:

### Contract Traceability (added to 23 specs)

| Spec | Contract Added |
|------|---------------|
| F-049 | `contracts/sdk-boundary.md`, `contracts/deny-destroy.md` |
| F-050 | `contracts/deny-destroy.md` — DenyHook:MUST:1 |
| F-051 | `contracts/event-vocabulary.md` |
| F-052 | `contracts/streaming-contract.md`, `contracts/event-vocabulary.md` |
| F-053 | `contracts/error-hierarchy.md` |
| F-054 | N/A (already complete — response extraction is internal) |
| F-055 | `contracts/streaming-contract.md` |
| F-056 | `contracts/sdk-boundary.md` |
| F-057 | `contracts/sdk-boundary.md`, `contracts/provider-protocol.md` |
| F-058 | `contracts/provider-protocol.md`, `contracts/error-hierarchy.md` |
| F-059 | `contracts/provider-protocol.md` |
| F-060 | `contracts/error-hierarchy.md` |
| F-061 | `contracts/error-hierarchy.md` |
| F-062 | `contracts/deny-destroy.md` |
| F-063 | `contracts/sdk-boundary.md` |
| F-064 | N/A (packaging concern, no contract) |
| F-065 | `contracts/provider-protocol.md` |
| F-066 | `contracts/error-hierarchy.md` |
| F-067 | `contracts/provider-protocol.md`, `contracts/deny-destroy.md` |
| F-068 | `contracts/event-vocabulary.md` |
| F-069 | N/A — dead code removal |
| F-070 | N/A — code quality cleanup |
| F-071 | N/A — unused field removal |

### Test File Specificity (improved in 14 specs)

Specs that had generic "Test: ..." entries were updated with specific test file paths:

- F-051: `tests/test_event_config_loading.py` or `tests/test_streaming.py`
- F-052: `tests/test_real_sdk_streaming.py`
- F-053: `tests/test_error_config_loading.py` or `tests/test_error_translation.py`
- F-054: `tests/test_response_extraction.py` or `tests/test_provider.py`
- F-055: `tests/test_streaming_accumulator.py` or `tests/test_streaming.py`
- F-056: `tests/test_sdk_client.py`
- F-057: `tests/test_provider_lifecycle.py` or `tests/test_provider.py`
- F-058: `tests/test_timeout_enforcement.py` or `tests/test_provider.py`
- F-059: `tests/test_multi_turn_context.py`
- F-060: `tests/test_retry.py`
- F-061: `tests/test_error_translation.py`
- F-064: `tests/test_config_loading.py`
- F-066: `tests/test_error_translation.py`
- F-068: `tests/test_event_classification.py` or `tests/test_streaming.py`

### Test Specificity for Cleanup Specs

- F-071: Added instruction to search `tests/` for `system_prompt`/`max_tokens` references

## STATE.yaml Verification

All 23 features verified present in STATE.yaml with correct entries:

| Feature | Status | Priority | Present |
|---------|--------|----------|---------|
| F-049 | ready | P0 | ✅ |
| F-050 | ready | P0 | ✅ |
| F-051 | ready | P0 | ✅ |
| F-052 | ready | P0 | ✅ |
| F-053 | ready | P1 | ✅ |
| F-054 | ready | P1 | ✅ |
| F-055 | ready | P1 | ✅ |
| F-056 | ready | P1 | ✅ |
| F-057 | ready | P1 | ✅ |
| F-058 | ready | P1 | ✅ |
| F-059 | ready | P1 | ✅ |
| F-060 | ready | P2 | ✅ |
| F-061 | ready | P2 | ✅ |
| F-062 | ready | P2 | ✅ |
| F-063 | ready | P2 | ✅ |
| F-064 | ready | P2 | ✅ |
| F-065 | ready | P2 | ✅ |
| F-066 | ready | P2 | ✅ |
| F-067 | ready | P2 | ✅ |
| F-068 | ready | P2 | ✅ |
| F-069 | ready | P2 | ✅ |
| F-070 | ready | P2 | ✅ |
| F-071 | ready | P2 | ✅ |

Priority distribution: 4× P0, 7× P1, 12× P2

## Per-Spec Audit Notes

### F-049: Fix Architecture Test Paths (P0)
- **Problem**: Precise — cites `test_contract_deny_destroy.py:81` and `test_sdk_client.py:191`
- **TDD**: Write red test with assertion `files_scanned > 0`, then fix path
- **Scope**: Tight — path fix only

### F-050: Mandatory Deny Hook Installation (P0)
- **Problem**: Cites `provider.py:256-257`, `client.py:241-243`, contract clause `DenyHook:MUST:1`
- **TDD**: Write test with mock session lacking `register_pre_tool_use_hook`, expect `ProviderUnavailableError`
- **Scope**: Well-bounded

### F-051: Defensive Event Config Loading (P0)
- **Problem**: Cites `streaming.py:211-212`, contrasts with existing defensive pattern
- **TDD**: Write tests with malformed YAML configs, expect `ConfigurationError`
- **Scope**: Well-bounded

### F-052: Real SDK Streaming Pipeline (P0)
- **Problem**: Cites `provider.py:479-498`, explains full impact chain
- **TDD**: Write integration test expecting event sequence, then wire streaming
- **Risk**: Largest P0 spec — touches production SDK path

### F-053: Unify Error Config Loading (P1)
- **Problem**: Cites `client.py:72-113`, explains F-036 regression
- **TDD**: Write test verifying `context_extraction` via importlib path
- **Scope**: Well-bounded

### F-054: Response Extraction Recursion Guard (P1)
- **Problem**: Cites `provider.py:144-145`, explains stack overflow scenario
- **TDD**: Write test with chained `.data` attributes, verify termination
- **Scope**: Minimal — 3-line fix

### F-055: Streaming Accumulator Completion Guard (P1)
- **Problem**: Cites `streaming.py:78-95`, explains corruption scenario
- **TDD**: Write test sending CONTENT_DELTA after TURN_COMPLETE
- **Scope**: Minimal — 1-line guard

### F-056: SDK Client Failed-Start Cleanup (P1)
- **Problem**: Cites `client.py:199-214`, explains cascading failure
- **TDD**: Write test with failing `start()`, verify retry works
- **Scope**: Well-bounded

### F-057: Provider Close Cleanup (P1)
- **Problem**: Cites `provider.py:517-523`, security impact (token exposure)
- **TDD**: Write test verifying `client.close()` called on `provider.close()`
- **Scope**: Minimal

### F-058: SDK Request Timeout Enforcement (P1)
- **Problem**: Cites `provider.py:481-483`, `config/models.yaml`
- **TDD**: Write test with slow mock, expect `LLMTimeoutError`
- **Scope**: Well-bounded

### F-059: ChatRequest Multi-Turn Context (P1)
- **Problem**: Cites `provider.py:443-458`, explains content type loss
- **TDD**: Write test with mixed content types, verify preservation
- **Risk**: SDK API surface may constrain approach

### F-060: Config-Driven Retry (P2)
- **Problem**: Cites `config/retry.yaml` as dead data
- **TDD**: Write test with retryable error mock, verify retry count
- **Scope**: New module creation

### F-061: Error Config Missing Mappings (P2)
- **Problem**: Cites specific missing patterns (AbortError, session lifecycle)
- **TDD**: Write test with abort-pattern SDK error, verify mapping
- **Scope**: Config + code additions

### F-062: Architecture Test Hardening (P2)
- **Problem**: Cites DEF-009 and DEF-013 with specific weakness descriptions
- **TDD**: Write test with planted violation key, verify detection
- **Scope**: Test improvements only

### F-063: SDK Boundary Structure (P2)
- **Problem**: Cites contract divergence with specific missing files
- **TDD**: Write architecture test for `_imports.py` quarantine, then create file
- **Risk**: Touches module structure — needs careful import chain verification

### F-064: PyPI Publishing Readiness (P2)
- **Problem**: Cites `config/` path, `pyproject.toml` gaps, wheel issues
- **TDD**: Write test for package-relative config loading, then move config
- **Risk**: Config path change affects many files — coordinate with F-053

### F-065: Provider Decomposition (P2)
- **Problem**: Cites `provider.py` at 532 lines vs 120 target
- **TDD**: Existing tests serve as regression — refactor until they pass
- **Risk**: Largest refactor — ensure no behavioral change

### F-066: Error Translation Safety (P2)
- **Problem**: Cites DEF-010 (substring matching) and DEF-014 (constructor TypeError)
- **TDD**: Write negative matching tests, then fix matching logic
- **Scope**: Well-bounded

### F-067: Test Quality Improvements (P2)
- **Problem**: Cites 4 specific defects with line references
- **TDD**: Fix each test quality issue individually
- **Scope**: Test-only changes (plus one redundant import removal)

### F-068: Event Classification Overlap Validation (P2)
- **Problem**: Cites `streaming.py:231-240`, explains silent priority issue
- **TDD**: Write test with overlapping config, expect `ConfigurationError`
- **Scope**: Well-bounded

### F-069: Remove `_complete_fn` Dead Code (P2)
- **Problem**: Cites `provider.py:35`, confirmed dead by code-intel
- **TDD**: Existing tests — removal should be transparent
- **Scope**: Minimal

### F-070: Clean Up Deferred Imports (P2)
- **Problem**: Cites `provider.py:250,259,274`, confirmed no circular risk
- **TDD**: Existing tests + `python -c` import verification
- **Scope**: Minimal

### F-071: Remove Unused SessionConfig Fields (P2)
- **Problem**: Cites `types.py`, confirmed unused by code-intel
- **TDD**: Existing tests — removal should be transparent
- **Scope**: Minimal

## Final Verification

- **23/23 specs** have all 8 criteria satisfied
- **23/23 features** present in STATE.yaml with status `ready`
- **0 blockers** identified
- **All specs are dev-machine ready** for implementation via `.dev-machine/build.yaml`

## Recommended Implementation Order

Based on priority and dependency analysis:

### Wave 1 (P0 — do first, order matters)
1. **F-049** — fix test paths (unblocks F-062)
2. **F-050** — mandatory deny hook
3. **F-051** — defensive event config loading
4. **F-052** — real SDK streaming pipeline (largest, depends on nothing)

### Wave 2 (P1 — independent, can parallelize)
5. **F-055** — accumulator guard (1-line fix)
6. **F-054** — recursion guard (3-line fix)
7. **F-056** — client failed-start cleanup
8. **F-057** — provider close cleanup
9. **F-058** — timeout enforcement
10. **F-053** — unify error config (coordinate with F-064)
11. **F-059** — multi-turn context

### Wave 3 (P2 — cleanup/refactoring)
12. **F-069** — remove dead code (trivial)
13. **F-070** — cleanup imports (trivial)
14. **F-071** — remove unused fields (trivial)
15. **F-062** — architecture test hardening (after F-049)
16. **F-068** — event classification validation
17. **F-066** — error translation safety
18. **F-061** — error config missing mappings
19. **F-067** — test quality improvements
20. **F-060** — config-driven retry (new module)
21. **F-063** — SDK boundary structure (refactor)
22. **F-064** — PyPI publishing readiness (config move)
23. **F-065** — provider decomposition (largest refactor, do last)
