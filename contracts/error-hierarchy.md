# Contract: Error Hierarchy

## Version
- **Current:** 1.1 (v2.2 Path-Corrected)
- **Module Reference:** amplifier_module_provider_github_copilot/error_translation.py
- **Correction:** 2026-03-15 — Removed erroneous `src/` prefix
- **Config:** config/errors.yaml
- **Kernel Source:** `amplifier_core.llm_errors`
- **Status:** Specification

---

## Overview

This contract defines the error translation requirements for the provider. The provider MUST translate SDK errors into kernel error types from `amplifier_core.llm_errors`. Custom error types are NOT allowed — they break cross-provider error handling.

---

## Kernel Error Hierarchy

All errors come from `amplifier_core.llm_errors`:

```
LLMError (base)
├── AuthenticationError (HTTP 401/403)
│   └── AccessDeniedError (HTTP 403 - permission denied)
├── RateLimitError (HTTP 429, retryable=True)
│   └── QuotaExceededError (billing limit, retryable=False)
├── LLMTimeoutError (retryable=True)
├── ContentFilterError (safety filter)
├── ProviderUnavailableError (HTTP 5xx, retryable=True)
│   └── NetworkError (connection failure, retryable=True)
├── NotFoundError (HTTP 404 - model not found)
├── ContextLengthError (HTTP 413 - context exceeded)
├── InvalidRequestError (HTTP 400/422)
├── StreamError (mid-stream connection failure, retryable=True)
├── AbortError (caller cancellation)
├── InvalidToolCallError (malformed tool call)
└── ConfigurationError (setup problems)
```

---

## Base Error Attributes

All `LLMError` subclasses have:

```python
class LLMError(Exception):
    provider: str | None       # Provider name (e.g., "github-copilot")
    model: str | None          # Model identifier
    status_code: int | None    # HTTP status code
    retryable: bool            # Whether retry is appropriate
    retry_after: float | None  # Seconds to wait before retry
    delay_multiplier: float    # Backoff delay multiplier (default 1.0)
```

---

## SDK → Kernel Error Mapping

| SDK Error Pattern | Kernel Error | Retryable |
|-------------------|--------------|-----------|
| `AuthenticationError`, 401, 403 | `AuthenticationError` | No |
| `RateLimitError`, 429 | `RateLimitError` | Yes |
| `QuotaExceededError` | `QuotaExceededError` | No |
| `TimeoutError` | `LLMTimeoutError` | Yes |
| `ContentFilterError`, safety | `ContentFilterError` | No |
| `ConnectionError`, 5xx | `ProviderUnavailableError` | Yes |
| `ProcessExitedError`, network | `NetworkError` | Yes |
| `ModelNotFoundError`, 404 | `NotFoundError` | No |
| Session errors | `ProviderUnavailableError` | Yes |
| Circuit breaker | `ProviderUnavailableError` | No |
| Stream interruption | `StreamError` | Yes |
| Abort signal | `AbortError` | No |

---

## Config Schema (errors.yaml)

```yaml
version: "1.0"

error_mappings:
  - sdk_patterns: ["AuthenticationError", "InvalidTokenError", "PermissionDeniedError"]
    string_patterns: ["401", "403", "unauthorized", "permission denied"]
    kernel_error: AuthenticationError
    retryable: false

  - sdk_patterns: ["RateLimitError"]
    string_patterns: ["429", "rate limit"]
    kernel_error: RateLimitError
    retryable: true
    extract_retry_after: true

  - sdk_patterns: ["QuotaExceededError"]
    string_patterns: ["quota exceeded", "billing"]
    kernel_error: QuotaExceededError
    retryable: false

  - sdk_patterns: ["TimeoutError", "RequestTimeoutError"]
    string_patterns: ["timeout", "timed out"]
    kernel_error: LLMTimeoutError
    retryable: true

  - sdk_patterns: ["ContentFilterError", "SafetyError"]
    string_patterns: ["content filter", "safety", "blocked"]
    kernel_error: ContentFilterError
    retryable: false

  - sdk_patterns: ["ConnectionError", "ProcessExitedError"]
    string_patterns: ["connection refused", "process exited"]
    kernel_error: NetworkError
    retryable: true

  - sdk_patterns: ["ModelNotFoundError"]
    string_patterns: ["model not found", "404"]
    kernel_error: NotFoundError
    retryable: false

default:
  kernel_error: ProviderUnavailableError
  retryable: true
```

---

## Translation Function

```python
from amplifier_core.llm_errors import (
    LLMError,
    AuthenticationError,
    RateLimitError,
    LLMTimeoutError,
    ContentFilterError,
    ProviderUnavailableError,
    NetworkError,
    NotFoundError,
)

def translate_sdk_error(
    exc: Exception,
    config: ErrorConfig,
    *,
    provider: str = "github-copilot",
    model: str | None = None,
) -> LLMError:
    """
    Translate SDK exception to kernel LLMError.
    
    Contract: error-hierarchy.md
    
    - MUST NOT raise (always returns)
    - MUST use config patterns (no hardcoded mappings)
    - MUST chain original via `raise X from exc`
    - MUST set provider attribute
    """
```

---

## MUST Constraints

1. **MUST** use kernel error types from `amplifier_core.llm_errors`
2. **MUST NOT** create custom error classes
3. **MUST** set `provider="github-copilot"` on all errors
4. **MUST** preserve original exception via chaining (`raise X from original`)
5. **MUST** use config-driven pattern matching
6. **MUST** fall through to `ProviderUnavailableError(retryable=True)` for unknown errors

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `error-hierarchy:Kernel:MUST:1` | Uses kernel types only |
| `error-hierarchy:Kernel:MUST:2` | Sets provider attribute |
| `error-hierarchy:Translation:MUST:1` | Never raises |
| `error-hierarchy:Translation:MUST:2` | Uses config patterns |
| `error-hierarchy:Translation:MUST:3` | Chains original exception |
| `error-hierarchy:RateLimit:MUST:1` | Extracts retry_after |
| `error-hierarchy:Default:MUST:1` | Falls through to ProviderUnavailableError |

---

## Implementation Checklist

- [ ] Import all error types from `amplifier_core.llm_errors`
- [ ] Config file has all pattern mappings
- [ ] Translation function uses config patterns
- [ ] All errors set `provider="github-copilot"`
- [ ] Original exception chained via `raise ... from`
- [ ] Rate limit extracts retry_after from message
- [ ] Unknown errors default to ProviderUnavailableError
