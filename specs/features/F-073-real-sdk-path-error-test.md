# F-073: Add Tests for Real SDK Path Error Handling

**Status:** ready
**Priority:** P1
**Source:** deep-review/code-navigator-v2.md

## Problem Statement
Only `test_f043_sdk_response.py` exercises the real SDK path, and it mocks the entire session — no real error handling is tested. There are no tests verifying that SDK exceptions raised during `send_and_wait()` are correctly translated to kernel error types via the error translation layer added in F-072.

Evidence: `grep "_client.session" tests/` shows only 1 test file, which mocks everything including error paths.

## Success Criteria
- [ ] Tests exist that mock `send_and_wait()` to raise various SDK exception types
- [ ] Each raised exception is verified to translate to the correct kernel error type
- [ ] Coverage includes: timeout, rate limit, authentication, and generic SDK errors
- [ ] Tests verify `LLMError` subclasses pass through without double-wrapping
- [ ] Tests match exception types defined in `config/errors.yaml`

## Implementation Approach
Create a new test file `tests/test_f072_sdk_error_translation.py` that:

1. Sets up a `GitHubCopilotProvider` with a mocked `_client`
2. Mocks `_client.session()` to return an async context manager with a mock `sdk_session`
3. Configures `sdk_session.send_and_wait()` to raise specific exception types
4. Calls `provider.complete()` and asserts the correct kernel error type is raised

Test cases:
- `TimeoutError` → `LLMTimeoutError`
- `PermissionError` / auth-like errors → `AuthenticationError`
- `ConnectionError` / rate limit errors → `RateLimitError`
- Generic `RuntimeError` → `LLMProviderError` (fallback)
- `LLMError` subclass → passes through unchanged (no double-wrap)

## Files to Modify
- New: `tests/test_f072_sdk_error_translation.py`

## TDD Anchor
- Red: Write tests expecting kernel error types from SDK exceptions → tests fail (no try/except in complete())
- Green: F-072 implementation makes them pass
- Refactor: Parameterize test cases if repetitive

## Contract Traceability
- `contracts/error-hierarchy.md` — "The provider MUST translate SDK errors into kernel error types"

## Not In Scope
- Testing streaming path error handling (see F-052)
- Testing error translation logic itself (covered by existing `test_error_translation.py`)
- Adding new error types or mappings (see F-061)
