# Module Spec: Error Translation

**Module:** `src/provider_github_copilot/error_translation.py`
**Contract:** `contracts/error-hierarchy.md`
**Config:** `config/errors.yaml`
**Target Size:** ~80 lines

---

## Purpose

Config-driven translation from SDK exceptions to domain exceptions. The Python code contains NO hardcoded error mappings — all mappings live in YAML.

---

## Public API

```python
def translate_sdk_error(
    exc: Exception,
    config: ErrorConfig,
) -> CopilotProviderError:
    """
    Translate SDK exception to domain exception.
    
    Contract: error-hierarchy.md
    
    - MUST NOT raise (always returns)
    - MUST preserve original in .original attribute
    - MUST use config patterns (no hardcoded mappings)
    - MUST fall through to CopilotProviderError(retryable=False)
    """
```

---

## Domain Exception Hierarchy

```
CopilotProviderError (base, retryable=False)
├── CopilotAuthError (retryable=False, always)
├── CopilotRateLimitError (retryable=True, retry_after extracted)
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
  - sdk_patterns: ["AuthenticationError", "InvalidTokenError"]
    string_patterns: ["401", "403"]
    domain_error: CopilotAuthError
    retryable: false

  - sdk_patterns: ["RateLimitError", "QuotaExceededError"]
    string_patterns: ["429"]
    domain_error: CopilotRateLimitError
    retryable: true
    extract_retry_after: true

default:
  domain_error: CopilotProviderError
  retryable: false
```

---

## Implementation Pattern

```python
DOMAIN_ERROR_MAP = {
    "CopilotAuthError": CopilotAuthError,
    "CopilotRateLimitError": CopilotRateLimitError,
    # ... all domain errors
}

def translate_sdk_error(exc: Exception, config: ErrorConfig) -> CopilotProviderError:
    exc_type = type(exc).__name__
    exc_message = str(exc)
    
    for mapping in config.error_mappings:
        if _matches(exc_type, exc_message, mapping):
            return _create_domain_error(mapping, exc)
    
    # Fallback
    return CopilotProviderError(str(exc), retryable=False, original=exc)
```

---

## Invariants

1. **MUST NOT:** Raise — always return a domain exception
2. **MUST:** Preserve original exception in `.original`
3. **MUST:** Use config patterns for all matching
4. **MUST NOT:** Hardcode any error type mappings in Python

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Each domain error type has correct attributes |
| Config | Config mappings produce expected domain errors |
| Property | Random exceptions always return a domain error |
| Contract | Each MUST clause in error-hierarchy.md tested |
