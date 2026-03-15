# Module Spec: Session Factory

**Module:** `amplifier_module_provider_github_copilot/sdk_adapter/client.py`
**Contract:** `contracts/deny-destroy.md`
**Target Size:** ~250 lines

---

## Purpose

Creates ephemeral SDK sessions with deny hooks installed. Implements the Deny + Destroy pattern via CopilotClientWrapper.

---

## Public API

```python
class CopilotClientWrapper:
    """Wrapper around copilot.CopilotClient with lifecycle management."""
    
    @asynccontextmanager
    async def session(
        self,
        model: str | None = None,
        *,
        system_message: str | None = None,
    ) -> AsyncIterator[Any]:
        """
        Create an ephemeral session with proper cleanup.
        
        Contract: deny-destroy.md
        
        - MUST install deny_permission_request handler
        - MUST destroy session on context exit
        - MUST NOT allow session reuse
        """

def create_deny_hook() -> Callable[[Any, Any], Awaitable[dict[str, str]]]:
    """Create async deny hook for SDK pre_tool_use callback."""

def deny_permission_request(request: Any, invocation: dict[str, str]) -> Any:
    """Deny all permission requests at source (F-033)."""
```

---

## Session Lifecycle

```
complete() called
    │
    ▼
CopilotClientWrapper.session()
    │
    ├── Get or create SDK client (with deny_permission_request)
    ├── Create SDK session with streaming=True
    ├── Yield raw SDK session
    │
    ▼
[Session used for one turn]
    │
    ▼
Context manager exits
    │
    └── Session disconnected (resources released)
```

---

## Deny Hook Implementation

```python
DENY_ALL: dict[str, str] = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty - tools executed by kernel only",
}

def create_deny_hook() -> Callable[[Any, Any], Awaitable[dict[str, str]]]:
    """Create async deny hook for SDK pre_tool_use callback."""
    async def deny(input_data: Any, invocation: Any) -> dict[str, str]:
        return DENY_ALL
    return deny

def deny_permission_request(request: Any, invocation: dict[str, str]) -> Any:
    """
    Deny all permission requests at source.
    
    F-033: SDK v0.1.33 requires on_permission_request handler.
    This is the FIRST line of defense. preToolUse deny hook is the second.
    
    Contract: contracts/deny-destroy.md
    """
    from copilot.types import PermissionRequestResult
    return PermissionRequestResult(
        kind="denied-by-rules",
        message="Amplifier orchestrator controls all operations",
    )
```

---

## Invariants (from deny-destroy.md)

### Hook Installation
1. **MUST:** Install deny_permission_request on client creation
2. **MUST:** Hook returns "denied-by-rules" for all permission requests
3. **MUST NOT:** Have any configuration to disable the hooks

### Session Ephemerality
1. **MUST:** Create new session per complete() call
2. **MUST:** Disconnect session after context exit
3. **MUST NOT:** Reuse sessions across calls
4. **MUST NOT:** Accumulate state in sessions

---

## Dependencies

```
sdk_adapter/client.py
├── imports: copilot.CopilotClient, copilot.types.PermissionRequestResult
├── imports: ../error_translation (for error config)
├── uses: deny_permission_request, create_deny_hook
└── enforces: deny-destroy.md contract
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Deny hook returns DENY for all inputs |
| Integration | Session created and destroyed correctly |
| Contract | All deny-destroy.md MUST clauses tested |
| Negative | Verify no code path skips hook installation |
