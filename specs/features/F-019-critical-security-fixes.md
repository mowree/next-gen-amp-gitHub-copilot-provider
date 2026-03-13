# F-019: Critical Security Fixes

**Priority**: CRITICAL
**Source**: security-guardian, bug-hunter, code-navigator
**Estimated Lines**: ~50 changes

## Objective

Fix all critical security vulnerabilities identified by the expert panel review.

## Acceptance Criteria

### AC-1: Deny Hook on Real SDK Path (CRITICAL)

**Problem**: Deny hook is only installed on test/injected path, not on `CopilotClientWrapper.session()`.

**Fix**: In `sdk_adapter/client.py`, the `session()` context manager MUST register the deny hook.

```python
# In CopilotClientWrapper.session()
@asynccontextmanager
async def session(self, ...):
    sdk_session = await client.create_session(session_config)
    # MUST register deny hook here
    if hasattr(sdk_session, "register_pre_tool_use_hook"):
        sdk_session.register_pre_tool_use_hook(create_deny_hook())
    try:
        yield sdk_session
    finally:
        await sdk_session.disconnect()
```

**Test**: Add test that verifies deny hook fires when using `CopilotClientWrapper.session()` directly.

### AC-2: Fix Race Condition in session() (CRITICAL)

**Problem**: Concurrent calls to `session()` can use unstarted client due to async yield.

**Fix**: Add `asyncio.Lock` to guard lazy client initialization.

```python
class CopilotClientWrapper:
    _client_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def _get_client(self) -> CopilotClient:
        async with self._client_lock:
            if self._owned_client is None:
                self._owned_client = CopilotClient(options)
                await self._owned_client.start()
            return self._owned_client
```

**Test**: Add test with concurrent `session()` calls verifying no race.

### AC-3: Fix Double Exception Translation (HIGH)

**Problem**: Already-translated `LLMError` gets re-wrapped by `translate_sdk_error`.

**Fix**: In `provider.py` `complete()`, add guard before translation:

```python
except Exception as e:
    if isinstance(e, LLMError):
        raise  # Already translated, don't wrap again
    kernel_error = translate_sdk_error(e, error_config, ...)
    raise kernel_error from e
```

**Test**: Verify `LLMError` raised inside `complete()` is not double-wrapped.

## Files to Modify

- `src/amplifier_module_provider_github_copilot/sdk_adapter/client.py`
- `src/amplifier_module_provider_github_copilot/provider.py`
- `tests/test_security_fixes.py` (create)

## Contract References

- `contracts/deny-destroy.md` — sovereignty contract
- `mydocs/debates/GOLDEN_VISION_V2.md` — Section "Non-Negotiable Constraints"

## NOT IN SCOPE

- Protocol method additions (separate feature F-020)
- Bundle.md creation (separate feature F-022)
