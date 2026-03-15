# F-082: Wire provider.close() to Call client.close()

**Status:** ready
**Priority:** P1
**Source:** deep-review/integration-specialist.md, principal-review
**Supersedes:** F-057 (same fix, stronger evidence from principal review)

## Problem Statement

`GitHubCopilotProvider.close()` at `provider.py:517-523` is a no-op (`pass`), but `CopilotClientWrapper.close()` at `sdk_adapter/client.py:258-268` exists and properly cleans up resources by stopping the owned SDK client. This means provider resources are never cleaned up — the SDK client process remains alive after provider shutdown, leaking resources and extending token exposure.

## Evidence

**provider.py lines 517-523 — NO-OP:**
```python
async def close(self) -> None:
    """Clean up provider resources."""
    # Currently no resources to clean up
    pass
```

**sdk_adapter/client.py lines 258-268 — HAS IMPLEMENTATION:**
```python
async def close(self) -> None:
    """Clean up owned client resources. Safe to call multiple times."""
    if self._owned_client is not None:
        try:
            logger.info("[CLIENT] Stopping owned Copilot client...")
            await self._owned_client.stop()
            logger.info("[CLIENT] Copilot client stopped")
        except Exception as e:
            logger.warning(f"[CLIENT] Error stopping client: {e}")
        finally:
            self._owned_client = None
```

## Success Criteria

- [ ] `provider.close()` delegates to `self._client.close()`
- [ ] Defensive: safe when `_client` is not initialized or is `None`
- [ ] Idempotent: calling `close()` twice does not error
- [ ] Test verifies `client.close()` is called when `provider.close()` is called

## Implementation Approach

Replace the no-op in `GitHubCopilotProvider.close()` with:

```python
async def close(self) -> None:
    """Clean up provider resources."""
    if hasattr(self, '_client') and self._client:
        await self._client.close()
```

`CopilotClientWrapper.close()` is already idempotent (sets `_owned_client = None` after stop), so no additional guard is needed in the provider.

## Files to Modify

- `amplifier_module_provider_github_copilot/provider.py` (lines 517-523)

## Contract Traceability

- `contracts/provider-protocol.md` — `close()` is part of the provider lifecycle; providers should clean up resources
- `contracts/sdk-boundary.md` — provider must clean up SDK resources on close

## Tests Required

Additions to `tests/test_provider.py` or new `tests/test_provider_lifecycle.py`:
- Test: `provider.close()` calls `client.close()`
- Test: `provider.close()` is safe when `_client` not initialized
- Test: `provider.close()` is idempotent (two calls, no error)

## Not In Scope

- Connection pooling
- Graceful shutdown sequencing
- Timeout on close

## 7. Test Strategy (TDD)

Write tests BEFORE implementation:

| Test | Type | What it verifies | Contract Anchor |
|------|------|------------------|-----------------|
| `test_happy_path` | Unit | Primary behavior | `<contract>:<Section>:MUST:N` |
| `test_error_case` | Unit | Error handling | `<contract>:<Section>:MUST:N` |
| `test_edge_case` | Unit | Boundary conditions | `<contract>:<Section>:SHOULD:N` |

**Test file:** `tests/test_<module_name>.py`

Tests MUST:
- Reference contract clause in docstring
- Use `ConfigCapturingMock` for SDK boundary tests
- Fail before implementation (Red phase)
