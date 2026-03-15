# F-086: Handle Session Disconnect Failures Properly

**Status:** ready
**Priority:** P2 (MEDIUM)
**Source:** principal-review

## Problem Statement

At `client.py:252-256`, disconnect failures are swallowed with only a warning log. No metrics or escalation occur, hiding operational issues during cleanup.

## Evidence

```python
except Exception as e:
    _logger.warning("Session disconnect failed", exc_info=e)
    # No metrics, no escalation, just swallowed
```

Disconnect failures are silently lost — no counter, no escalation for repeated failures, no operational visibility.

## Success Criteria

- [ ] Disconnect failures increment a failure counter
- [ ] Repeated disconnect failures (>3) escalate to `_logger.error` with resource-leak warning
- [ ] All existing tests pass
- [ ] New test covers disconnect failure counting and escalation

## Implementation Approach

Add error metrics and escalation for repeated failures:

```python
except Exception as e:
    _logger.warning("Session disconnect failed", exc_info=e)
    self._disconnect_failures += 1
    if self._disconnect_failures > 3:
        _logger.error("Multiple disconnect failures — potential resource leak")
```

Initialize `self._disconnect_failures = 0` in `__init__`.

## Files to Modify

- `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (add counter + escalation logic)

## Contract Traceability

- **Observability** — failures should be tracked for operational awareness
- **Resource safety** — repeated disconnect failures may indicate resource leaks

## Tests Required

- Unit test: verify `_disconnect_failures` increments on disconnect failure
- Unit test: verify escalation to `_logger.error` after >3 failures
- Verify existing tests still pass

## Not In Scope

- Structured metrics/telemetry export (future observability feature)
- Automatic reconnection or recovery after disconnect failure
- Disconnect failure handling in other components
