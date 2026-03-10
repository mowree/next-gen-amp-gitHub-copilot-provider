# F-010: SDK Client Wrapper

## 1. Overview

**Module:** sdk_adapter/client.py
**Priority:** P0
**Depends on:** F-001-sdk-adapter-skeleton

Wrapper around `copilot.CopilotClient` with lifecycle management, auth status checking, and error handling.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/sdk_adapter/client.py
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@dataclass(frozen=True)
class AuthStatus:
    """Authentication status from SDK."""
    is_authenticated: bool | None
    github_user: str | None
    auth_type: str | None = None
    error: str | None = None

class CopilotClientWrapper:
    """Wrapper around copilot.CopilotClient with lifecycle management."""
    
    async def get_auth_status(self) -> AuthStatus:
        """Check authentication status without creating session."""
        ...
    
    @asynccontextmanager
    async def session(self, model: str | None = None) -> AsyncIterator[CopilotSessionWrapper]:
        """Create ephemeral session with proper cleanup."""
        ...
    
    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from SDK."""
        ...
    
    async def close(self) -> None:
        """Clean up client resources."""
        ...
```

### Behavior

- Import `copilot.CopilotClient` from SDK
- Check `COPILOT_AGENT_TOKEN` environment variable for auth
- Session context manager MUST destroy session on exit (success or error)
- Translate SDK exceptions to domain errors
- Log SDK lifecycle events at DEBUG level

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `CopilotClientWrapper` class exists | Import test |
| AC-2 | `get_auth_status()` returns AuthStatus | Unit test with mock |
| AC-3 | `session()` context manager destroys on exit | Unit test |
| AC-4 | SDK import isolated to this file | grep verification |
| AC-5 | Proper error translation for auth failures | Unit test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No COPILOT_AGENT_TOKEN | AuthStatus.is_authenticated=False, clear error message |
| Invalid token | AuthenticationError with provider="github-copilot" |
| SDK not installed | ImportError with installation instructions |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../sdk_adapter/client.py` | Create | CopilotClientWrapper |
| `tests/test_sdk_client.py` | Create | Client wrapper tests |

## 6. Reference

- `reference-only/amplifier-module-provider-github-copilot/.../client.py` lines 1-100
- `reference-only/copilot-sdk/python/copilot/client.py`
