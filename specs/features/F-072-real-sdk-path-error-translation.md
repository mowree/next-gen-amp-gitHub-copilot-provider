# F-072: Add Error Translation to GitHubCopilotProvider.complete()

**Status:** ready
**Priority:** P0
**Source:** deep-review/code-navigator-v2.md

## Problem Statement
The `GitHubCopilotProvider.complete()` method (provider.py lines 420-530) has NO try/except around the `async with self._client.session()` block. If `sdk_session.send_and_wait()` raises, raw SDK exceptions bubble directly to the kernel.

Evidence:
- `client.py:248-256` — `yield sdk_session` has only `finally` (disconnect), no `except`
- `provider.py:481-495` — `async with self._client.session()` has no try/except
- `translate_sdk_error` is only called during client init (212-214) and session creation (244-246)

Contract violated: `contracts/error-hierarchy.md` — "The provider MUST translate SDK errors into kernel error types"

## Success Criteria
- [ ] All exceptions from `sdk_session.send_and_wait()` are caught and translated to kernel error types
- [ ] Already-translated `LLMError` subclasses pass through without double-wrapping
- [ ] Error translation uses existing `translate_sdk_error` from `error_translation.py`
- [ ] No raw SDK exceptions escape `complete()` under any failure mode

## Implementation Approach
Wrap the `async with self._client.session(model=model)` block in `complete()` with try/except:

```python
try:
    async with self._client.session(model=model) as sdk_session:
        sdk_response = await sdk_session.send_and_wait(...)
        # ... existing response handling ...
except LLMError:
    raise  # Already translated — pass through
except Exception as e:
    from .error_translation import load_error_config, translate_sdk_error
    error_config = load_error_config(Path(__file__).parent.parent / "config" / "errors.yaml")
    raise translate_sdk_error(e, error_config, provider="github-copilot", model=model) from e
```

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (lines ~481-495, add try/except around session block)

## Tests Required
- Covered by F-073 (dedicated test feature)

## TDD Anchor
- Red: `sdk_session.send_and_wait()` raises `RuntimeError` → currently bubbles raw → after fix, translated to `LLMProviderError`
- Green: Add try/except with `translate_sdk_error`
- Refactor: None expected

## Contract Traceability
- `contracts/error-hierarchy.md` — "The provider MUST translate SDK errors into kernel error types"

## Not In Scope
- Changing error translation logic itself (see F-066)
- Adding new error mappings (see F-061)
- Error handling in streaming path (see F-052)
