# F-058: SDK Request Timeout Enforcement

**Status:** ready
**Priority:** P1
**Source:** deep-review/security-guardian.md (Finding #2)
**Defect ID:** N/A

## Problem Statement
The real SDK path in `provider.py:481-483` calls `send_and_wait()` with no timeout enforcement. `config/models.yaml` defines `timeout: 60` but no code reads or applies it. A hung SDK call holds provider resources indefinitely, degrading availability.

## Success Criteria
- [ ] SDK calls are wrapped with `asyncio.timeout()` using configured timeout
- [ ] Timeout value is read from `config/models.yaml`
- [ ] Timeout expiry raises `LLMTimeoutError` (via error translation)
- [ ] Test verifies timeout is enforced

## Implementation Approach
1. Read timeout from model config (default 60s)
2. Wrap SDK calls in `async with asyncio.timeout(timeout_s):`
3. Catch `asyncio.TimeoutError` and translate to `LLMTimeoutError`

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (SDK call paths)

## Contract Traceability
- `contracts/provider-protocol.md` — provider must handle timeouts gracefully
- `contracts/error-hierarchy.md` — `LLMTimeoutError` is a defined kernel error type

## Tests Required
- `tests/test_timeout_enforcement.py` (new) or additions to `tests/test_provider.py`:
  - Test: SDK call exceeding timeout raises `LLMTimeoutError`
  - Test: normal calls within timeout succeed

## Not In Scope
- Concurrency limiting
- Circuit breaker implementation
- Per-model timeout overrides
