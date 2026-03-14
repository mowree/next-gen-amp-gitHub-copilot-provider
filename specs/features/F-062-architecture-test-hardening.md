# F-062: Architecture Test Hardening

**Status:** ready
**Priority:** P2
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-009, DEF-013

## Problem Statement
Multiple architecture/contract tests have structural weaknesses:
1. `TestDenyHookNotConfigurable` (DEF-009): Only catches YAML keys containing both "deny" AND "disable", or literal `allow_tool_execution`. Keys like `bypass_hook`, `skip_sovereignty_check` pass through.
2. Config path tests (DEF-013): Use relative `Path("config")` with no assertion that files were actually found. Running pytest from a non-root directory scans zero files.

## Success Criteria
- [ ] Deny-hook config test uses a comprehensive deny list or pattern approach
- [ ] All path-based tests assert files were found before iterating
- [ ] Tests use `Path(__file__).parent.parent / "config"` for robust path resolution
- [ ] Test: planted violation key is caught

## Implementation Approach
1. Expand deny-hook config test to check for broader patterns: `bypass`, `skip`, `disable`, `allow`, `override`, `hook`
2. Add `assert config_files, "No config files found"` assertions
3. Use `__file__`-relative paths instead of CWD-relative

## Files to Modify
- `tests/test_contract_deny_destroy.py` (lines 55-73, 81)
- `tests/test_contract_errors.py` (line 145)

## Tests Required
- Existing tests should be more robust (self-testing)

## Not In Scope
- Adding new contract tests
- Config schema validation
