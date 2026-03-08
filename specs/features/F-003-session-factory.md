# F-003: Session Factory with Deny Hook

## 1. Overview

**Module:** session_factory
**Priority:** P0
**Depends on:** F-001-sdk-adapter-skeleton

Ephemeral session creation with `preToolUse` deny hook. Every SDK session is created with a hook that denies all tool execution (Amplifier's orchestrator handles tools). Sessions are destroyed immediately after the first turn.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/session_factory.py
from sdk_adapter import SDKSession, SessionConfig

async def create_ephemeral_session(
    config: SessionConfig,
    *,
    deny_all_tools: bool = True,
) -> SDKSession:
    """
    Create an ephemeral SDK session with deny hook.
    
    Contract: deny-destroy.md
    
    - MUST register preToolUse hook that denies all tools
    - Session is ephemeral - caller MUST destroy after use
    """
    ...

def create_deny_hook() -> Callable:
    """
    Create a preToolUse hook that denies all tool execution.
    
    Returns a function that, when called by the SDK, returns
    a denial response preventing tool execution.
    """
    ...

async def destroy_session(session: SDKSession) -> None:
    """
    Destroy an ephemeral session.
    
    - MUST call session.disconnect() (not destroy())
    - MUST handle already-destroyed sessions gracefully
    """
    ...
```

### Behavior

- `create_ephemeral_session` creates a session via SDK adapter
- The deny hook is ALWAYS registered (deny_all_tools=True is default, not configurable at runtime)
- When SDK calls `preToolUse`, the hook returns a denial
- `destroy_session` calls `session.disconnect()` (SDK 0.1.32+ API)
- Sessions are single-use: create, get response, destroy

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | Session created with deny hook registered | Unit test with mock SDK |
| AC-2 | Deny hook returns denial for all tool calls | Unit test |
| AC-3 | destroy_session calls disconnect() | Unit test with mock |
| AC-4 | destroy_session handles already-destroyed gracefully | Unit test |
| AC-5 | No tool execution occurs (tools are captured, not executed) | Integration test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| SDK raises on session creation | Translate to NetworkError |
| Session already destroyed | No error, log warning |
| Disconnect raises | Log error, don't propagate |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/amplifier_module_provider_github_copilot/session_factory.py` | Create | Session factory functions |
| `tests/test_session_factory.py` | Create | Session lifecycle tests |

## 6. Dependencies

- F-001 sdk_adapter (for SDKSession, SessionConfig)

## 7. Notes

- Reference: contracts/deny-destroy.md (NON-NEGOTIABLE)
- The deny hook is the provider's defining commitment
- Evidence: Session a1a0af17 had 305 turns from a single request due to retry loops
- Circuit breaker (F-006) provides additional protection
