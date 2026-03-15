# F-076: Fix Async Mock Warning in Tests

**Status:** ready
**Priority:** P2
**Source:** deep-review/code-quality-reviewer.md

## Problem Statement
pytest shows 3 warnings: "coroutine 'create_deny_hook.<locals>.deny_hook' was never awaited" at client.py:242. The `register_pre_tool_use_hook()` receives an async hook function but the mock doesn't await it.

Root cause: Test mocks for `register_pre_tool_use_hook` don't handle async callables correctly, causing unawaited coroutine warnings that mask real issues.

## Success Criteria
- [ ] pytest runs with zero "coroutine was never awaited" warnings
- [ ] `register_pre_tool_use_hook` mock properly handles async hook functions
- [ ] No behavioral changes to production code
- [ ] All existing tests continue to pass

## Implementation Approach
Replace the `MagicMock` used for `register_pre_tool_use_hook` with `AsyncMock`, OR create a test double that properly captures and awaits async hooks passed to it.

Specifically:
1. Find test fixtures that mock `register_pre_tool_use_hook`
2. Change to `AsyncMock` so the hook coroutine is properly awaited
3. Run pytest and verify warnings are eliminated

## Files to Modify
- Test files that mock `register_pre_tool_use_hook` (likely in `tests/` — grep for `register_pre_tool_use_hook`)

## TDD Anchor
- Red: `pytest -W error::RuntimeWarning` fails due to unawaited coroutine
- Green: Replace with `AsyncMock` → warning eliminated
- Refactor: Ensure consistent async mock usage across test suite

## Contract Traceability
- Test quality — warnings should not be ignored as they can mask real bugs

## Not In Scope
- Changing production deny hook logic
- Changing hook registration API
- Other test warnings unrelated to async mocks
