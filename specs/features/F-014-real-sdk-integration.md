# F-014: Real SDK Integration

## 1. Overview

**Module:** sdk_adapter/driver.py (complete implementation)
**Priority:** P0
**Depends on:** F-010-sdk-client-wrapper, F-013-event-router

Wire the SDK adapter stubs to actual copilot SDK calls. Replace NotImplementedError with real implementation.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py (complete)
from collections.abc import Callable, AsyncIterator
from typing import Any

from .types import SDKSession, SessionConfig
from .client import CopilotClientWrapper
from .event_handler import SdkEventHandler
from .loop_control import LoopController, ToolCaptureStrategy

async def create_session(
    config: SessionConfig,
    deny_hook: Callable[..., Any] | None = None,
    client: CopilotClientWrapper | None = None,
) -> SDKSession:
    """Create a new SDK session with deny hook.
    
    Args:
        config: Session configuration
        deny_hook: Hook to deny tool execution (registered on session)
        client: Optional client (for testing). Creates new if None.
    
    Returns:
        SDKSession wrapper around real copilot session
    """
    ...

async def destroy_session(session: SDKSession) -> None:
    """Destroy an SDK session.
    
    Calls session.disconnect() (SDK 0.1.32+ API).
    Handles already-destroyed gracefully.
    """
    ...

async def stream_completion(
    session: SDKSession,
    prompt: str,
    tools: list[dict[str, Any]] | None = None,
) -> AsyncIterator[Any]:
    """Stream events from SDK session.
    
    Yields raw SDK events for processing by event handler.
    """
    ...
```

### Behavior

- Import `copilot.CopilotClient` and `CopilotSession`
- Register `preToolUse` hook via SDK's hook API
- Use `session.send()` for message streaming
- Call `session.disconnect()` on destroy (not `destroy()`)
- Wrap SDK exceptions with domain error translation

### SDK API Reference

From `reference-only/copilot-sdk/python/copilot/session.py`:
- `session.on(callback)` — subscribe to events
- `session.send({"prompt": "..."})` — send message
- Session is context manager for cleanup

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `create_session` returns working SDKSession | Integration test (requires token) |
| AC-2 | Deny hook registered on session | Unit test with mock |
| AC-3 | `destroy_session` calls disconnect | Unit test with mock |
| AC-4 | `stream_completion` yields events | Unit test with mock |
| AC-5 | SDK exceptions translated | Unit test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No COPILOT_AGENT_TOKEN | AuthenticationError |
| Session already destroyed | Log warning, no error |
| SDK process crashes | NetworkError with details |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../sdk_adapter/driver.py` | Modify | Replace NotImplementedError with real code |
| `tests/test_sdk_driver_real.py` | Create | Real SDK tests (skipped without token) |

## 6. Reference

- `reference-only/amplifier-module-provider-github-copilot/.../client.py` lines 100-300
- `reference-only/copilot-sdk/python/copilot/session.py` lines 44-100
