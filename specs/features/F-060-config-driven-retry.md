# F-060: Config-Driven Retry Implementation

**Status:** ready
**Priority:** P2
**Source:** deep-review/integration-specialist.md
**Defect ID:** N/A

## Problem Statement
`config/retry.yaml` defines retry policy (exponential backoff with jitter, max 3 attempts) and circuit breaker settings (soft/hard turn limits), but no Python code reads or implements this config. When a retryable error occurs, it is translated with `retryable=True` but no retry attempt is made at the provider level. The config is dead data.

## Success Criteria
- [ ] `config/retry.yaml` is loaded and parsed
- [ ] Retryable errors trigger automatic retry with configured backoff
- [ ] Max attempts is respected
- [ ] Jitter is applied to backoff delays
- [ ] Non-retryable errors are NOT retried
- [ ] Tests verify retry behavior

## Implementation Approach
1. Add retry config loader (similar to error/event config loaders)
2. Implement retry loop in `complete()` around SDK call
3. Apply exponential backoff with jitter from config
4. Respect `max_attempts` from config

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (add retry wrapper)
- New: retry config loading utility (could be in `streaming.py` or new `retry.py`)

## Tests Required
- Test: retryable error retries up to max_attempts
- Test: non-retryable error fails immediately
- Test: backoff delay increases between retries
- Test: all retries exhausted raises the last error

## Not In Scope
- Circuit breaker implementation (separate feature)
- Kernel-level retry coordination
