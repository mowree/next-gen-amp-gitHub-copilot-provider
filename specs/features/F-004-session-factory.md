# Feature Spec: F-004 Session Factory with Deny Hook

**Feature ID:** F-004
**Module:** `src/provider_github_copilot/session_factory.py`
**Contract:** `contracts/deny-destroy.md`
**Priority:** P0 (Foundation)
**Estimated Size:** ~100 lines

---

## Summary

Implement the session factory that creates ephemeral SDK sessions with the deny hook installed. This is the core of the Deny + Destroy pattern.

---

## Acceptance Criteria

1. **Session factory created:** `session_factory.py`
   - `create_ephemeral_session()` async context manager
   - `make_deny_all_hook()` function

2. **Deny hook behavior:**
   - Returns DENY for ALL tool execution requests
   - No configuration to disable (mechanism, not policy)

3. **Session lifecycle:**
   - New session per `complete()` call
   - Session destroyed on context exit
   - No state accumulation

4. **Tests verify contract compliance**

---

## Interfaces

```python
# src/provider_github_copilot/session_factory.py

from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Any

from .sdk_adapter import SessionHandle, SessionConfig

@asynccontextmanager
async def create_ephemeral_session(
    client: Any,  # CopilotClient (typed later)
    config: SessionConfig,
) -> AsyncIterator[SessionHandle]:
    """
    Create an ephemeral session with deny hook.
    
    Contract: deny-destroy.md
    
    - MUST install preToolUse deny hook
    - MUST destroy session on context exit
    - MUST NOT allow session reuse
    
    Yields:
        SessionHandle: Opaque handle to the session (UUID string)
    """
    ...


def make_deny_all_hook() -> Callable[[Any], dict[str, str]]:
    """
    Create the deny hook for tool execution.
    
    Returns a hook that denies ALL tool execution requests.
    This is NON-CONFIGURABLE per deny-destroy.md constraint #6.
    
    Returns:
        Callable that returns {"action": "DENY", "reason": "..."}
    """
    def deny_all(tool_request: Any) -> dict[str, str]:
        return {
            "action": "DENY",
            "reason": "Amplifier orchestrator handles tool execution"
        }
    return deny_all
```

---

## Implementation Notes

### SDK Integration (deferred)

The actual SDK session creation will use:
```python
# In sdk_adapter/_imports.py (to be added in this feature)
from github_copilot_sdk import CopilotSession, CopilotClient
```

For now, we implement the pattern with a mock/stub to verify the architecture.

### Deny Hook Installation

```python
# The deny hook is installed during session creation
session = await client.create_session(
    model=config.model,
    system_message=config.system_message,
    tools=config.tools,
    hooks={
        "preToolUse": make_deny_all_hook()
    }
)
```

### Session Handle Generation

```python
import uuid

def _generate_handle() -> SessionHandle:
    return str(uuid.uuid4())
```

---

## Test Cases

```python
# tests/test_session_factory.py

import pytest
from provider_github_copilot.session_factory import (
    create_ephemeral_session,
    make_deny_all_hook,
)
from provider_github_copilot.sdk_adapter import SessionConfig


@pytest.mark.contract("deny-destroy:DenyHook:MUST:2")
def test_deny_hook_returns_deny():
    """Deny hook returns DENY for all tool requests."""
    hook = make_deny_all_hook()
    result = hook({"name": "read_file", "args": {}})
    assert result["action"] == "DENY"


@pytest.mark.contract("deny-destroy:DenyHook:MUST:2")
def test_deny_hook_denies_any_tool():
    """Deny hook denies regardless of tool name."""
    hook = make_deny_all_hook()
    for tool_name in ["read_file", "write_file", "bash", "any_tool"]:
        result = hook({"name": tool_name})
        assert result["action"] == "DENY"


@pytest.mark.asyncio
@pytest.mark.contract("deny-destroy:Ephemeral:MUST:1")
async def test_session_created_per_call():
    """Each context manager invocation creates a new session."""
    # Uses mock client
    ...


@pytest.mark.asyncio  
@pytest.mark.contract("deny-destroy:Ephemeral:MUST:2")
async def test_session_destroyed_on_exit():
    """Session is destroyed when context manager exits."""
    # Verify cleanup is called
    ...
```

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/provider_github_copilot/session_factory.py` | Create | ~80 |
| `src/provider_github_copilot/sdk_adapter/_imports.py` | Update | ~20 |
| `tests/test_session_factory.py` | Create | ~60 |
| `tests/conftest.py` | Update | ~20 (add contract marker) |

---

## Dependencies

- F-001 (SDK Adapter skeleton) — for SessionHandle, SessionConfig types

---

## Contract References

- `deny-destroy:DenyHook:MUST:1` — Hook installed on every session
- `deny-destroy:DenyHook:MUST:2` — Hook returns DENY
- `deny-destroy:Ephemeral:MUST:1` — New session per complete()
- `deny-destroy:Ephemeral:MUST:2` — Session destroyed after use
