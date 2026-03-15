# F-085: Add Timeout Enforcement to Real SDK Path

**Status:** ready
**Priority:** P1 (HIGH)
**Source:** principal-review

## Problem Statement

The real SDK path at `provider.py:479-495` has no timeout enforcement. The `send_and_wait()` call can block indefinitely, creating an availability risk.

## Evidence

- `grep -n "timeout" provider.py` returns zero matches — no timeout enforcement anywhere in the provider
- `send_and_wait()` has no timeout parameter or `asyncio.timeout` wrapper
- `config/models.yaml` already defines `timeout: 120` but it is never consumed by the SDK call path

## Success Criteria

- [ ] `send_and_wait()` call is wrapped in `asyncio.timeout` (or uses SDK timeout parameter if available)
- [ ] Timeout value is loaded from `config/models.yaml` (`timeout: 120`)
- [ ] `asyncio.TimeoutError` is caught and translated to a proper provider error
- [ ] All existing tests pass
- [ ] New test covers timeout enforcement behavior

## Implementation Approach

Wrap the SDK call in `asyncio.timeout`:

```python
import asyncio

async with asyncio.timeout(config.timeout_seconds):
    sdk_response = await sdk_session.send_and_wait({"prompt": ...})
```

Catch `asyncio.TimeoutError` and translate to a provider-level error with clear messaging.

## Files to Modify

- `amplifier_module_provider_github_copilot/provider.py` (wrap `send_and_wait()` in timeout)
- Possibly `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (if timeout should be enforced at client level)

## Contract Traceability

- **Availability** — operations must not block indefinitely
- **Security** — denial of service if SDK hangs; resource exhaustion if many sessions hang

## Tests Required

- Unit test: verify `asyncio.TimeoutError` is raised when SDK call exceeds timeout
- Unit test: verify timeout value is sourced from config
- Verify existing tests still pass

## Not In Scope

- Retry logic after timeout (covered by F-060)
- Circuit breaker patterns
- Timeout enforcement on other code paths (e.g., streaming)
