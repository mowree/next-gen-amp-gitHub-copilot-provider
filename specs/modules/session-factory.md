# Module Spec: Session Factory

**Module:** `src/provider_github_copilot/session_factory.py`
**Contract:** `contracts/deny-destroy.md`
**Target Size:** ~100 lines

---

## Purpose

Creates ephemeral SDK sessions with the deny hook installed. Implements the core Deny + Destroy pattern.

---

## Public API

```python
@asynccontextmanager
async def create_ephemeral_session(
    client: CopilotClient,
    config: SessionConfig,
) -> AsyncIterator[SessionHandle]:
    """
    Create an ephemeral session with deny hook.
    
    Contract: deny-destroy.md
    
    - MUST install preToolUse deny hook
    - MUST destroy session on context exit
    - MUST NOT allow session reuse
    """
    
def make_deny_all_hook() -> Callable:
    """
    Create the deny hook for tool execution.
    
    Returns a hook that denies ALL tool execution requests.
    This is non-configurable per deny-destroy.md.
    """
```

---

## Session Lifecycle

```
complete() called
    │
    ▼
create_ephemeral_session()
    │
    ├── Create SDK session with deny hook
    ├── Yield SessionHandle (UUID)
    │
    ▼
[Session used for one turn]
    │
    ▼
Context manager exits
    │
    └── Session destroyed (resources released)
```

---

## Deny Hook Implementation

```python
def make_deny_all_hook():
    """
    The deny hook — NON-CONFIGURABLE.
    
    This is mechanism, not policy. No YAML knob.
    Per GOLDEN_VISION_V2.md Non-Negotiable Constraint #6.
    """
    def deny_all(tool_request):
        return {
            "action": "DENY",
            "reason": "Amplifier orchestrator handles tool execution"
        }
    return deny_all
```

---

## Invariants (from deny-destroy.md)

### Hook Installation
1. **MUST:** Install preToolUse deny hook on every session
2. **MUST:** Hook returns DENY for all tool requests
3. **MUST NOT:** Have any configuration to disable the hook

### Session Ephemerality
1. **MUST:** Create new session per complete() call
2. **MUST:** Destroy session after first turn
3. **MUST NOT:** Reuse sessions across calls
4. **MUST NOT:** Accumulate state in sessions

---

## Dependencies

```
session_factory.py
├── imports: sdk_adapter.SessionHandle, sdk_adapter.SessionConfig
├── uses: CopilotClient (from client.py)
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
