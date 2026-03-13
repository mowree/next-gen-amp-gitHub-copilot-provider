# F-035: Error Type Expansion

## 1. Overview

**Module:** error_translation
**Priority:** P0 (circuit breaker fix), P1-P4 (new error types)
**Depends on:** F-002-error-translation

This feature adds 5 missing kernel error types to make error messages actionable, and fixes a critical bug where circuit breaker messages incorrectly match LLMTimeoutError (causing infinite retry loops).

## 2. Requirements

### Interfaces

```python
# New error classes (using existing factory pattern)
ContextLengthError = _make_error_class("ContextLengthError", False)
InvalidRequestError = _make_error_class("InvalidRequestError", False)
StreamError = _make_error_class("StreamError", True)  # Retryable
InvalidToolCallError = _make_error_class("InvalidToolCallError", False)
ConfigurationError = _make_error_class("ConfigurationError", False)
```

### Behavior

- Circuit breaker pattern MUST be matched BEFORE timeout pattern (order matters)
- Circuit breaker errors MUST have `retryable=false`
- Token/context limit errors → ContextLengthError (retryable=false)
- Stream interruptions → StreamError (retryable=true)
- Tool conflicts → InvalidToolCallError (retryable=false)
- Model config errors → ConfigurationError (retryable=false)
- SDK error messages are preserved unchanged (no rewriting)

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | Circuit breaker pattern exists in errors.yaml with `retryable: false` | Unit test |
| AC-2 | Circuit breaker pattern index < timeout pattern index | Unit test |
| AC-3 | "Circuit breaker TRIPPED: timeout=..." → ProviderUnavailableError (not LLMTimeoutError) | Unit test |
| AC-4 | ContextLengthError class exists and in KERNEL_ERROR_MAP | Unit test |
| AC-5 | "413", "token count", "exceeds the limit" patterns → ContextLengthError | Unit test |
| AC-6 | StreamError class exists with retryable=True | Unit test |
| AC-7 | "GOAWAY", "broken pipe" patterns → StreamError | Unit test |
| AC-8 | InvalidToolCallError class exists with retryable=False | Unit test |
| AC-9 | "tool conflict", "fake tool" patterns → InvalidToolCallError | Unit test |
| AC-10 | ConfigurationError class exists with retryable=False | Unit test |
| AC-11 | "does not support" patterns → ConfigurationError | Unit test |
| AC-12 | All existing tests pass (no regressions) | `pytest tests/` |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Message matches both circuit breaker AND timeout | Circuit breaker wins (earlier in config list) |
| Message is empty string | Fall through to ProviderUnavailableError default |
| Message has "timeout" but not circuit breaker context | Match LLMTimeoutError |
| 400 error without "token count" | Should NOT match ContextLengthError |
| Generic "connection error" | Fall through to NetworkError (existing) |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../error_translation.py` | Modify | +5 error classes, +5 KERNEL_ERROR_MAP entries, +logger import |
| `config/errors.yaml` | Modify | +6 pattern mappings (circuit breaker FIRST, then P1-P4) |
| `tests/test_f035_error_types.py` | Create | All P0-P4 test cases (class existence, pattern matching, edge cases) |

## 6. Dependencies

- No new dependencies

## 7. Notes

- Detailed implementation plan: `docs/plans/2026-03-13-f035-error-type-expansion.md`
- Implementation follows TDD: write failing tests first, then implement
- hooks.emit() and correlation IDs deferred to future feature (no coordinator.hooks pattern in codebase)
- AbortError deferred (requires orchestrator changes)
- SDK messages already actionable; improvement is TYPE routing, not message rewriting
