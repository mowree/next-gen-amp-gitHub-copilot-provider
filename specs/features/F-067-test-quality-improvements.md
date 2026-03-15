# F-067: Test Quality Improvements

**Status:** ready
**Priority:** P2
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-012, DEF-015, DEF-016, DEF-018

## Problem Statement
Several test quality issues identified:
1. **DEF-012**: No test for `mount()` exception → returns `None` path
2. **DEF-015**: `MagicMock()` without `spec=` in contract tests allows false passes
3. **DEF-016**: Concurrent session test doesn't verify deny hook installation per session
4. **DEF-018**: Redundant `from pathlib import Path` import inside `complete()` (already at module level)

## Success Criteria
- [ ] `mount()` failure test added (returns None, logs error)
- [ ] Contract test mocks use `spec=` where appropriate
- [ ] Concurrent session test verifies deny hook on each session
- [ ] Redundant import removed from `provider.py:233-234`
- [ ] All existing tests still pass

## Implementation Approach
1. Add mount failure test to `tests/`
2. Add `spec=` to MagicMock usage in `test_contract_protocol.py`
3. Add deny hook assertion to `test_concurrent_sessions.py`
4. Remove redundant `from pathlib import Path` in `provider.py:233`

## Files to Modify
- `tests/test_contract_protocol.py` (add spec= to mocks)
- `tests/test_concurrent_sessions.py` (add deny hook verification)
- `amplifier_module_provider_github_copilot/provider.py` (remove redundant import, line 233-234)
- New or existing test file for mount failure test

## Tests Required
- Test: mount() with broken provider init → returns None
- Improved existing tests (spec= on mocks, deny hook verify)

## Contract Traceability
- `contracts/provider-protocol.md` — mount() behavior is part of provider lifecycle
- `contracts/deny-destroy.md` — deny hook must be verified on concurrent sessions

## Not In Scope
- Rewriting test architecture
- Adding new test frameworks
