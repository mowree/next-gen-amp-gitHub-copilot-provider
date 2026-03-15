# F-077: Delete Tombstone Test Files

**Status:** ready
**Priority:** P3
**Source:** deep-review/code-quality-reviewer.md

## Problem Statement
Two test files are empty tombstones containing only "This file has been deleted" comments:
- `tests/test_deny_hook_breach_detector.py`
- `tests/test_ephemeral_session_wiring.py`

These serve no purpose, clutter the test suite, and confuse developers who encounter them.

## Success Criteria
- [ ] Both tombstone files are deleted
- [ ] No test collection errors after deletion
- [ ] No references to these files remain in config or CI

## Implementation Approach
Delete both files. Verify no other files reference them.

## Files to Modify
- `tests/test_deny_hook_breach_detector.py` (delete)
- `tests/test_ephemeral_session_wiring.py` (delete)

## TDD Anchor
- Red: Files exist with no test content
- Green: Files deleted, `pytest --collect-only` shows no change in collected tests
- Refactor: N/A

## Contract Traceability
- Code hygiene — dead files should be removed

## Not In Scope
- Re-implementing the tests these files once contained
- Other test file cleanup
