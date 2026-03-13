# F-036: Error Context Enhancement

## 1. Overview

**Module:** error_translation
**Priority:** P1
**Depends on:** F-035-error-type-expansion

Enhance error context in translated errors to improve debuggability. When errors are translated from SDK to kernel types, include structured context that helps developers and AI agents understand what went wrong without guessing.

**Expert Consensus:** This feature was approved by zen-architect, amplifier-expert, and integration-specialist as "improving existing translation fidelity" without adding new scope or violating the Three-Medium Architecture.

## 2. Requirements

### Interfaces

```python
# No new interfaces - enhances existing translate_sdk_error() output

# Example enhanced error context (via error message or attributes):
InvalidToolCallError(
    "External tool 'apply_patch' conflicts with built-in tool",
    provider="github-copilot",
    model="claude-opus-4.5",
    retryable=False,
    # Enhanced context (in message or structured field):
    # tool_name="apply_patch", conflict_type="built-in"
)
```

### Behavior

- Error messages MUST preserve original SDK message unchanged
- Error messages MAY append structured context in `[context: key=value]` format
- Context extraction patterns defined in `config/errors.yaml`
- Context extraction MUST NOT fail or modify error on regex failure
- Logging MUST emit DEBUG-level log with extracted context

### Config Extension

```yaml
# config/errors.yaml - new optional field per mapping
- sdk_patterns: ["InvalidToolCallError"]
  string_patterns: ["tool conflict", "conflicts with"]
  kernel_error: InvalidToolCallError
  retryable: false
  # NEW: Optional context extraction
  context_extraction:
    - pattern: 'tool["\']?\\s*["\']?([^"\'\\s]+)'
      field: tool_name
    - pattern: '(built-in|external|missing)'
      field: conflict_type
```

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `ErrorMapping` dataclass has optional `context_extraction` field | Unit test |
| AC-2 | `translate_sdk_error()` extracts context when patterns match | Unit test |
| AC-3 | Context extraction failure does NOT prevent error translation | Unit test |
| AC-4 | DEBUG log emitted with extracted context | Log inspection test |
| AC-5 | Extracted context appears in error message or attributes | Unit test |
| AC-6 | Empty tool arguments (`{}`) triggers warning log | Unit test |
| AC-7 | All existing tests pass (no regressions) | `pytest tests/` |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Regex pattern fails to match | Context field omitted, error still translated |
| Multiple patterns, one fails | Successful extractions included, failures omitted |
| Empty message string | No context extraction attempted |
| Context value contains special characters | Properly escaped in log/message |
| Tool call with empty arguments `{}` | Warning logged, error translated normally |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../error_translation.py` | Modify | +`context_extraction` field in `ErrorMapping`, +extraction logic in `translate_sdk_error()`, +logger import if missing |
| `config/errors.yaml` | Modify | +`context_extraction` patterns for InvalidToolCallError, ConfigurationError |
| `tests/test_f036_error_context.py` | Create | Tests for context extraction, failure handling, empty args warning |

## 6. Dependencies

- No new dependencies

## 7. Notes

- This feature adds ~20 lines to error_translation.py
- The context extraction is observability-only; it does not change error routing
- Empty tool argument warning is logged at WARNING level, not DEBUG
- Future: Consider structured error attributes instead of message appending (requires kernel change)
- Expert approval: zen-architect confirmed this "improves existing responsibility without adding new scope"
