# F-049: Fix Architecture Fitness Test Paths

**Status:** ready
**Priority:** P0
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-001

## Problem Statement
Both architecture fitness tests (`test_contract_deny_destroy.py:81` and `test_sdk_client.py:191`) reference `src/amplifier_module_provider_github_copilot` — a path that does not exist. The actual package is at `amplifier_module_provider_github_copilot/` (no `src/` prefix). `Path.glob()` on a non-existent directory yields zero files, so both tests pass vacuously with zero assertions. The SDK boundary and deny-hook sovereignty guards have never scanned a single file.

## Success Criteria
- [ ] `test_no_sdk_imports_outside_adapter` scans actual source files
- [ ] `test_no_copilot_imports_in_domain_modules` scans actual source files
- [ ] Both tests assert that at least one file was scanned (no vacuous pass)
- [ ] Tests fail if an SDK import is placed in a non-adapter module (verify with intentional violation)
- [ ] All existing tests still pass

## Implementation Approach
1. Change `Path("src/amplifier_module_provider_github_copilot")` to `Path("amplifier_module_provider_github_copilot")` in both files
2. Add assertion: `assert files_scanned > 0, "No files found — check path"` after the glob loop in both tests

## Files to Modify
- `tests/test_contract_deny_destroy.py` (line 81)
- `tests/test_sdk_client.py` (line 191)

## Tests Required
- Existing tests should now actually scan files
- Verify tests catch a planted violation (manual check)

## Contract Traceability
- `contracts/sdk-boundary.md` — architecture tests enforce SDK import quarantine
- `contracts/deny-destroy.md` — architecture tests enforce deny hook sovereignty

## Not In Scope
- Refactoring the architecture fitness tests beyond path fix
- Adding new contract enforcement tests
