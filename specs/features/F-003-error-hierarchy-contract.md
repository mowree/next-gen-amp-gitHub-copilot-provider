# Feature Spec: F-003 Error Hierarchy Contract + Config

**Feature ID:** F-003
**Module:** `contracts/`, `config/`
**Contract:** `contracts/error-hierarchy.md`
**Config:** `config/errors.yaml`
**Priority:** P0 (Foundation)
**Estimated Size:** ~200 lines total

---

## Summary

Create the error hierarchy contract AND populate the error config. This establishes the domain exception taxonomy and config-driven error translation policy.

---

## Acceptance Criteria

1. **Contract file created:** `contracts/error-hierarchy.md`
   - Documents 8 domain exception types
   - Each has retryability, when raised, test anchors

2. **Config file populated:** `config/errors.yaml`
   - SDK pattern → domain error mappings
   - String pattern matching rules
   - Default fallback behavior

3. **Exception classes created:** `src/provider_github_copilot/exceptions.py`
   - All 8 domain exceptions
   - Base class with `retryable`, `original` attributes

4. **Tests pass** for exception attributes

---

## Domain Exception Hierarchy

```
CopilotProviderError (base, retryable=False)
├── CopilotAuthError (retryable=False, always)
├── CopilotRateLimitError (retryable=True, retry_after)
├── CopilotTimeoutError (retryable=True)
├── CopilotContentFilterError (retryable=False)
├── CopilotSessionError (retryable=True)
├── CopilotModelNotFoundError (retryable=False)
├── CopilotSubprocessError (retryable=True)
└── CopilotCircuitBreakerError (retryable=False)
```

---

## Config Schema (errors.yaml)

```yaml
version: "1.0"

error_mappings:
  - sdk_patterns: ["AuthenticationError", "InvalidTokenError", "PermissionDeniedError"]
    string_patterns: ["401", "403", "unauthorized", "permission denied"]
    domain_error: CopilotAuthError
    retryable: false

  - sdk_patterns: ["RateLimitError", "QuotaExceededError"]
    string_patterns: ["429", "rate limit", "quota exceeded"]
    domain_error: CopilotRateLimitError
    retryable: true
    extract_retry_after: true
    retry_after_pattern: "retry.after\\D*(\\d+(?:\\.\\d+)?)"

  - sdk_patterns: ["TimeoutError", "RequestTimeoutError"]
    string_patterns: ["timeout", "timed out"]
    domain_error: CopilotTimeoutError
    retryable: true

  - sdk_patterns: ["ContentFilterError", "SafetyError"]
    string_patterns: ["content filter", "safety", "blocked"]
    domain_error: CopilotContentFilterError
    retryable: false

  - sdk_patterns: ["SessionCreateError", "SessionDestroyError"]
    string_patterns: ["session"]
    domain_error: CopilotSessionError
    retryable: true

  - sdk_patterns: ["ModelNotFoundError", "ModelUnavailableError"]
    string_patterns: ["model not found", "model unavailable"]
    domain_error: CopilotModelNotFoundError
    retryable: false

  - sdk_patterns: ["ConnectionError", "ProcessExitedError"]
    string_patterns: ["connection refused", "process exited"]
    domain_error: CopilotSubprocessError
    retryable: true

default:
  domain_error: CopilotProviderError
  retryable: false
```

---

## Exception Classes

```python
# src/provider_github_copilot/exceptions.py

class CopilotProviderError(Exception):
    """Base exception for all provider errors."""
    
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        original: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.original = original


class CopilotAuthError(CopilotProviderError):
    """Authentication/authorization failure."""
    
    def __init__(self, message: str, *, original: Exception | None = None) -> None:
        super().__init__(message, retryable=False, original=original)


class CopilotRateLimitError(CopilotProviderError):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        original: Exception | None = None,
    ) -> None:
        super().__init__(message, retryable=True, original=original)
        self.retry_after = retry_after

# ... remaining exceptions
```

---

## Test Cases

```python
# tests/test_exceptions.py

def test_base_exception_attributes():
    """Base exception has retryable and original."""
    exc = CopilotProviderError("test", retryable=True, original=ValueError("orig"))
    assert exc.retryable is True
    assert isinstance(exc.original, ValueError)

def test_auth_error_never_retryable():
    """CopilotAuthError is always retryable=False."""
    exc = CopilotAuthError("auth failed")
    assert exc.retryable is False

def test_rate_limit_has_retry_after():
    """CopilotRateLimitError has retry_after attribute."""
    exc = CopilotRateLimitError("rate limited", retry_after=30)
    assert exc.retryable is True
    assert exc.retry_after == 30
```

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `contracts/error-hierarchy.md` | Create | ~100 |
| `config/errors.yaml` | Update | ~60 |
| `src/provider_github_copilot/exceptions.py` | Create | ~80 |
| `tests/test_exceptions.py` | Create | ~50 |

---

## Contract References

- `error-hierarchy:Base:MUST:1` — All inherit from CopilotProviderError
- `error-hierarchy:Base:MUST:2` — All have retryable attribute
- `error-hierarchy:Base:MUST:3` — All have original attribute
- `error-hierarchy:CopilotAuthError:MUST:1` — retryable=False always
- `error-hierarchy:CopilotRateLimitError:MUST:1` — retryable=True
- `error-hierarchy:CopilotRateLimitError:MUST:2` — Extract retry_after
