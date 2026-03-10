# F-015: Completion Module Wiring

## 1. Overview

**Module:** completion.py (wire to real SDK)
**Priority:** P0
**Depends on:** F-014-real-sdk-integration

Wire the completion module to use real SDK via sdk_adapter. Remove mock-only code paths.

## 2. Requirements

### Changes to completion.py

```python
# src/amplifier_module_provider_github_copilot/completion.py
# Current: Uses sdk_create_fn injection or NotImplementedError stubs
# Target: Uses real SDK adapter by default

async def complete(
    request: CompletionRequest,
    *,
    config: CompletionConfig | None = None,
) -> AsyncIterator[DomainEvent]:
    """Execute completion lifecycle with REAL SDK.
    
    1. Create ephemeral session via sdk_adapter.driver.create_session
    2. Register deny hook (always)
    3. Stream events via sdk_adapter.driver.stream_completion
    4. Route events through SdkEventHandler
    5. Yield DomainEvents
    6. Destroy session in finally block
    """
    ...
```

### Integration Points

| Current Code | Wire To |
|--------------|---------|
| `sdk_create_fn` injection | `sdk_adapter.driver.create_session` |
| Mock event streaming | `sdk_adapter.driver.stream_completion` |
| Direct event translation | `SdkEventHandler.handle_event` |

### Behavior

- Remove `sdk_create_fn` parameter (no longer needed for production)
- Keep injection for unit tests via `config.test_mode`
- Wire event handler to accumulator
- Ensure deny hook is ALWAYS registered

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `complete()` uses real SDK by default | Integration test |
| AC-2 | Deny hook registered on every session | Unit test |
| AC-3 | Events routed through SdkEventHandler | Unit test |
| AC-4 | Session destroyed on success | Integration test |
| AC-5 | Session destroyed on error | Integration test |
| AC-6 | Test mode still works with mocks | Unit test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| SDK timeout | LLMTimeoutError with provider="github-copilot" |
| Rate limit | RateLimitError with retry_after if available |
| Content filter | ContentFilterError |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../completion.py` | Modify | Wire to real SDK adapter |
| `tests/test_completion_integration.py` | Create | Integration tests |

## 6. Reference

- Current completion.py
- F-014 SDK integration spec
