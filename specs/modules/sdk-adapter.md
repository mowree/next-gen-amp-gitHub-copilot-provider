# Module Spec: SDK Adapter

**Module:** `amplifier_module_provider_github_copilot/sdk_adapter/`
**Contract:** `contracts/sdk-boundary.md`
**Target Size:** ~300 lines total

---

## Purpose

The SDK Adapter is **THE MEMBRANE** — the only place in the codebase where SDK imports are allowed. It wraps the Copilot SDK client and provides domain types.

---

## Files

| File | Lines | Responsibility |
|------|-------|----------------|
| `__init__.py` | ~20 | Public exports |
| `client.py` | ~250 | SDK client wrapper, deny hooks, session lifecycle |
| `types.py` | ~40 | Domain types (SessionConfig, SDKSession) |

---

## Public API

```python
# sdk_adapter/__init__.py

from .client import CopilotClientWrapper, create_deny_hook
from .types import SessionConfig

__all__ = [
    "CopilotClientWrapper",
    "SessionConfig",
    "create_deny_hook",
]
```

---

## Key Types

### SessionConfig
```python
@dataclass
class SessionConfig:
    """Configuration for creating an SDK session."""
    model: str
    system_prompt: str | None = None
    max_tokens: int | None = None
```

### SDKSession
```python
# Opaque type alias — domain code should not access SDK session internals
SDKSession = Any
```

### Deny Hooks
```python
def create_deny_hook() -> Callable[[Any, Any], Awaitable[dict[str, str]]]:
    """Async deny hook for SDK pre_tool_use callback."""

def deny_permission_request(request: Any, invocation: dict[str, str]) -> Any:
    """Deny all permission requests at source (F-033)."""
```

---

## Translation Strategy

**Wrap with deny hooks:**
- All SDK sessions get deny hooks installed automatically
- `create_deny_hook()` returns DENY for all tool execution requests
- `deny_permission_request()` denies all permission requests at source

**Note:** Error and event translation live in separate modules:
- `error_translation.py` (at package root)
- `streaming.py` (at package root)

---

## Invariants

1. **MUST NOT:** Export any SDK types (SDKSession is opaque Any)
2. **MUST NOT:** Allow SDK imports outside this package
3. **MUST:** Install deny hooks on every session creation
4. **MUST:** Return DENY for all tool execution requests
5. **MUST:** Deny all permission requests at source

---

## Dependencies

```
sdk_adapter/
├── imports: copilot (THE ONLY PLACE that imports SDK)
├── imports: ../error_translation (for error config loading)
└── exports: CopilotClientWrapper, SessionConfig, create_deny_hook
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Pure function tests for each translator |
| Property | Hypothesis tests: all valid SDK types map to domain types |
| Config | Verify config mappings produce correct outputs |
| Contract | Each MUST clause in sdk-boundary.md has a test |
