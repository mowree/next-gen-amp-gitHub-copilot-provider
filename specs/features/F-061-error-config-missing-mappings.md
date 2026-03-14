# F-061: Error Config Missing Mappings

**Status:** ready
**Priority:** P2
**Source:** deep-review/integration-specialist.md, deep-review/spec-reviewer-part3.md
**Defect ID:** N/A

## Problem Statement
`config/errors.yaml` is missing explicit mappings for:
1. `AbortError` — user aborts currently fall through to `ProviderUnavailableError(retryable=True)`, causing spurious retry on user-initiated cancellation
2. `SessionCreateError` / `SessionDestroyError` — session lifecycle errors fall to default

Additionally, the unknown-error fallback is `retryable=True`, while the Golden Vision spec's default is conservative non-retryable.

## Success Criteria
- [ ] `AbortError` mapping added with `retryable=false`
- [ ] Session lifecycle error patterns mapped appropriately
- [ ] Unknown-error default retryability reviewed (document decision if kept as-is)
- [ ] Tests verify abort pattern produces `AbortError`

## Implementation Approach
1. Add `AbortError` mapping to `config/errors.yaml` with appropriate SDK patterns
2. Add session lifecycle error patterns
3. Review and document the fallback retryability decision

## Files to Modify
- `config/errors.yaml`
- `amplifier_module_provider_github_copilot/error_translation.py` (add `AbortError` to `KERNEL_ERROR_MAP` if not present)

## Tests Required
- Test: abort-like SDK error produces `AbortError(retryable=False)`
- Test: session create failure produces appropriate error type

## Not In Scope
- Changing the error translation algorithm
- Adding error types not in amplifier_core
