# F-057: Provider Close Cleanup

**Status:** ready
**Priority:** P1
**Source:** deep-review/integration-specialist.md, deep-review/security-guardian.md
**Defect ID:** N/A

## Problem Statement
`GitHubCopilotProvider.close()` at `provider.py:517-523` is a no-op (`pass`). Mount cleanup calls `provider.close()`, but the owned `CopilotClientWrapper` (which has a working `close()` method at `client.py:258-267`) is never stopped. This leaves an authenticated SDK client process alive after provider cleanup, extending token exposure and consuming resources.

## Success Criteria
- [ ] `provider.close()` delegates to `self._client.close()`
- [ ] SDK client is stopped when provider is closed
- [ ] Close is idempotent (calling twice doesn't error)
- [ ] Test verifies client.close() is called on provider.close()

## Implementation Approach
1. Replace `pass` in `GitHubCopilotProvider.close()` with `await self._client.close()`
2. Handle case where client was never initialized

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (lines 517-523)

## Tests Required
- Test: `provider.close()` calls `client.close()`
- Test: `provider.close()` is safe when client not initialized

## Not In Scope
- Connection pooling
- Graceful shutdown sequencing
