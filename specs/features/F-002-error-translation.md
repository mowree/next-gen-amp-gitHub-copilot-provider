# F-002: Error Translation

## 1. Overview

**Module:** error_translation
**Priority:** P0
**Depends on:** F-001-sdk-adapter-skeleton

Config-driven error translation using kernel types from `amplifier_core.llm_errors`. SDK errors are translated to domain errors based on patterns in `config/errors.yaml`.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/error_translation.py
from amplifier_core.llm_errors import LLMError

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
    ...

@dataclass
class ErrorConfig:
    mappings: list[ErrorMapping]
    default_error: str
    default_retryable: bool

@dataclass
class ErrorMapping:
    sdk_patterns: list[str]
    string_patterns: list[str]
    kernel_error: str
    retryable: bool
    extract_retry_after: bool = False
```

### Behavior

- Load error mappings from `config/errors.yaml`
- Match SDK exception type name against `sdk_patterns`
- Match exception message against `string_patterns`
- Instantiate the corresponding kernel error type
- Always set `provider="github-copilot"` on errors
- Chain original exception: `raise X from original`
- Fall through to ProviderUnavailableError(retryable=True) for unknown errors

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | Translates known SDK errors to kernel types | Unit tests with mock exceptions |
| AC-2 | Uses config/errors.yaml for mappings | Config file parse test |
| AC-3 | Unknown errors become ProviderUnavailableError | Unit test |
| AC-4 | All errors have provider="github-copilot" | Unit test |
| AC-5 | Original exception chained via __cause__ | Unit test |
| AC-6 | RateLimitError extracts retry_after when present | Unit test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Exception message is None | Match by type only |
| Multiple patterns match | First match wins |
| Empty mappings list | Use default error |
| Invalid kernel_error name | Raise ConfigurationError |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/amplifier_module_provider_github_copilot/error_translation.py` | Create | translate_sdk_error function |
| `config/errors.yaml` | Modify | Full error mappings |
| `tests/test_error_translation.py` | Create | Translation tests |

## 6. Dependencies

- `amplifier-core` (for llm_errors types)
- `pyyaml` (for config loading)

## 7. Notes

- Reference: contracts/error-hierarchy.md
- Do NOT create custom error classes - use kernel types only
- The error_translation module is the ONLY place SDK errors are caught
