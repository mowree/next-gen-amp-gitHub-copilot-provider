# Module Spec: Error Translation

**Module:** `amplifier_module_provider_github_copilot/error_translation.py`
**Contract:** `contracts/error-hierarchy.md`
**Config:** `config/errors.yaml`
**Target Size:** ~200 lines

---

## Purpose

Config-driven translation from SDK exceptions to kernel error types. The Python code contains NO hardcoded error mappings — all mappings live in YAML.

---

## Public API

```python
from amplifier_core.llm_errors import LLMError

def translate_sdk_error(
    exc: Exception,
    config: ErrorConfig,
) -> LLMError:
    """
    Translate SDK exception to kernel error type.
    
    Contract: error-hierarchy.md
    
    - MUST NOT raise (always returns)
    - MUST preserve original in error attributes
    - MUST use config patterns (no hardcoded mappings)
    - MUST fall through to ProviderUnavailableError
    """
```

---

## Kernel Error Hierarchy

All errors from `amplifier_core.llm_errors`:

```
LLMError (base)
├── AuthenticationError (HTTP 401/403)
│   └── AccessDeniedError (HTTP 403 - permission denied)
├── RateLimitError (HTTP 429, retryable=True)
│   └── QuotaExceededError (billing limit, retryable=False)
├── LLMTimeoutError (retryable=True)
├── ContentFilterError (safety filter)
├── ProviderUnavailableError (HTTP 5xx, retryable=True)
├── ContextLengthError (token limit)
├── InvalidRequestError (malformed request)
├── NotFoundError (model not found)
├── StreamError (streaming failure)
├── InvalidToolCallError (tool call parsing)
├── ConfigurationError (config error)
└── AbortError (user abort)
```

---

## Config Schema (errors.yaml)

```yaml
version: "1.0"

error_mappings:
  - sdk_patterns: ["AuthenticationError", "InvalidTokenError"]
    string_patterns: ["401", "403"]
    kernel_error: AuthenticationError
    retryable: false

  - sdk_patterns: ["RateLimitError", "QuotaExceededError"]
    string_patterns: ["429"]
    kernel_error: RateLimitError
    retryable: true
    extract_retry_after: true

default:
  kernel_error: ProviderUnavailableError
  retryable: true
```

---

## Implementation Pattern

```python
from amplifier_core.llm_errors import LLMError, ProviderUnavailableError

KERNEL_ERROR_MAP: dict[str, type[LLMError]] = {
    "AuthenticationError": AuthenticationError,
    "RateLimitError": RateLimitError,
    "ProviderUnavailableError": ProviderUnavailableError,
    # ... all kernel error types
}

def translate_sdk_error(exc: Exception, config: ErrorConfig) -> LLMError:
    exc_type = type(exc).__name__
    exc_message = str(exc)
    
    for mapping in config.error_mappings:
        if _matches(exc_type, exc_message, mapping):
            return _create_kernel_error(mapping, exc)
    
    # Fallback
    return ProviderUnavailableError(str(exc))
```

---

## Invariants

1. **MUST NOT:** Raise — always return a kernel error type
2. **MUST:** Use kernel error types from `amplifier_core.llm_errors`
3. **MUST:** Use config patterns for all matching
4. **MUST NOT:** Define custom error types (use kernel types only)
5. **MUST:** Fall through to ProviderUnavailableError

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Each kernel error type maps correctly |
| Config | Config mappings produce expected kernel errors |
| Property | Random exceptions always return a kernel error |
| Contract | Each MUST clause in error-hierarchy.md tested |
