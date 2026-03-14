# F-056: SDK Client Failed-Start Cleanup

**Status:** ready
**Priority:** P1
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-007

## Problem Statement
In `client.py:199-214`, if `await self._owned_client.start()` raises, `self._owned_client` is already set to the partially-initialized `CopilotClient`. On the next call, `_get_client()` returns this broken client, skipping re-initialization. All subsequent sessions fail with confusing errors.

## Success Criteria
- [ ] Failed `start()` clears `self._owned_client` to `None`
- [ ] Next session attempt re-initializes the client
- [ ] The original exception is still propagated
- [ ] Test covers failed start → retry → success scenario

## Implementation Approach
1. Wrap `await self._owned_client.start()` in try/except
2. In except block: set `self._owned_client = None`, then re-raise

## Files to Modify
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (lines 199-214)

## Tests Required
- Test: `start()` raises → `_owned_client` is None → next call retries
- Test: `start()` succeeds → normal behavior (regression)

## Not In Scope
- Retry logic for client start
- Connection health monitoring
