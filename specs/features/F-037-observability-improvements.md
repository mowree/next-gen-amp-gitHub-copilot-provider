# F-037: Observability Improvements

## 1. Overview

**Module:** error_translation, tool_parsing
**Priority:** P2
**Depends on:** F-035-error-type-expansion

Add observability logging to help developers and AI agents diagnose issues without changing provider behavior. This feature adds warning logs for anomalous conditions (empty tool arguments) and debug logs for translation decisions.

**Expert Consensus:** Approved by amplifier-expert as using the existing hook pattern for observability. The provider's job is translation — these logs improve visibility into translation decisions without adding new responsibilities.

## 2. Requirements

### Interfaces

```python
# No new interfaces - adds logging to existing functions

# In error_translation.py
import logging
logger = logging.getLogger(__name__)

# In translate_sdk_error():
logger.debug(
    "[ERROR_TRANSLATION] %s -> %s (retryable=%s)",
    exc.__class__.__name__,
    kernel_error.__class__.__name__,
    kernel_error.retryable,
)

# In tool_parsing.py (for empty arguments warning):
if not tool_call.arguments:
    logger.warning(
        "[TOOL_PARSING] Empty arguments for tool '%s' (id=%s) - LLM may have hallucinated",
        tool_call.name,
        tool_call.id,
    )
```

### Behavior

- DEBUG log emitted for every successful error translation
- WARNING log emitted when tool arguments are empty `{}`
- Log format MUST use `[MODULE_NAME]` tag prefix (consistent with existing `[CLIENT]`, `[PROVIDER]` tags)
- Logging MUST NOT change return values or raise exceptions
- Logging MUST NOT log sensitive data (tokens, full prompts)

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `logger` imported in error_translation.py | Code inspection |
| AC-2 | DEBUG log emitted for every `translate_sdk_error()` call | Log capture test |
| AC-3 | Log includes original error type, kernel error type, retryable flag | Log content test |
| AC-4 | WARNING log emitted when `tool_call.arguments == {}` | Log capture test |
| AC-5 | Warning log includes tool name and ID | Log content test |
| AC-6 | Log format uses `[ERROR_TRANSLATION]` and `[TOOL_PARSING]` tags | Log format test |
| AC-7 | All existing tests pass (no regressions) | `pytest tests/` |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Tool arguments are `None` | No warning (None is different from empty dict) |
| Tool arguments are `{"key": ""}` | No warning (has keys, just empty values) |
| Error translation raises exception | Log exception at ERROR level before re-raising |
| Multiple tool calls, one with empty args | Warning logged for each empty one |
| Logging fails (IO error) | Silently swallowed, translation continues |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../error_translation.py` | Modify | +logger import (if not present), +DEBUG log in translate_sdk_error() |
| `src/.../tool_parsing.py` | Modify | +logger import, +WARNING log for empty arguments |
| `tests/test_f037_observability.py` | Create | Tests for log emission with caplog fixture |

## 6. Dependencies

- No new dependencies (uses standard library logging)

## 7. Notes

- Total addition: ~15 lines across two files
- Uses pytest's `caplog` fixture for testing log output
- Log level guidance:
  - DEBUG: Normal operations (every translation)
  - WARNING: Anomalous but handled (empty arguments)
  - ERROR: Failures that affect output
- Future: Consider structured logging (JSON) for better parsing
- Future: Consider hooks.emit() when coordinator pattern is established
