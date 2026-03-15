# F-090: Add Behavioral Tests for behaviors.md Contract

**Status:** ready
**Priority:** P1 (HIGH)
**Source:** manual-review

## Problem Statement

The `contracts/behaviors.md` defines MUST requirements for retry policy and circuit breaker behavior, but no tests verify these behaviors are implemented.

## Evidence

- behaviors.md contains MUST clauses for retry counts, backoff, jitter, circuit breaker thresholds
- Current tests (test_error_retry_config.py) verify error *patterns*, not retry *behavior*
- No tests verify: retry count is honored, backoff timing works, circuit breaker trips

## Success Criteria

- [ ] `test_behaviors.py` exists with tests for retry policy and circuit breaker
- [ ] Test verifies retry count is honored (exactly N retries, not N-1 or N+1)
- [ ] Test verifies circuit breaker trips after threshold failures
- [ ] Test verifies subsequent calls are rejected without hitting SDK after circuit trips
- [ ] All existing tests continue to pass
- [ ] Type checker (pyright) passes without new errors

## Implementation Approach

Create `tests/test_behaviors.py`:

```python
@pytest.mark.asyncio
async def test_retry_policy_honors_max_attempts():
    """Verify retry behavior matches behaviors.md contract."""
    # Mock SDK to fail N times
    # Verify exactly N retries attempted (not N-1, not N+1)
    pass

@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_threshold():
    """Verify circuit breaker per behaviors.md."""
    # Fail enough times to trip circuit
    # Verify subsequent calls are rejected without hitting SDK
    pass
```

TDD Note: May discover behaviors.md is aspirational and not implemented. That's acceptable discovery — test would fail and reveal gap.

## Files to Modify

- `tests/test_behaviors.py` (create)

## Contract Traceability

- **behaviors.md** — "Retry policy MUST honor max_attempts"
- **behaviors.md** — "Circuit breaker MUST trip after N failures"

## Tests Required

- Retry count honored exactly per contract
- Backoff timing follows contract specification
- Circuit breaker trips after threshold
- Post-trip calls rejected without SDK invocation

## Not In Scope

- Implementing retry/circuit breaker logic (that's a separate feature if missing)
- Performance benchmarking of retry timing
- Integration testing with real SDK failures
